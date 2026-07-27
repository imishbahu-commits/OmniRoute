import os from "os";
import path from "path";

/**
 * Lazy-loads the better-sqlite3 Database constructor.
 * Returns null if the native module is unavailable (graceful fallback).
 */
let _DatabaseCtor: (new (...args: any[]) => any) | null = null;

async function getDatabaseCtor(): Promise<(new (...args: any[]) => any) | null> {
  if (_DatabaseCtor !== undefined) return _DatabaseCtor;

  try {
    if (process.versions.bun) {
      const bunSqlite = await import("bun:sqlite");
      _DatabaseCtor = bunSqlite.Database;
    } else {
      const mod = await import("better-sqlite3");
      _DatabaseCtor = (mod.default ?? mod) as unknown as (new (...args: any[]) => any);
    }
  } catch {
    _DatabaseCtor = null;
  }
  return _DatabaseCtor;
}

function databaseOptions(readonly = false) {
  return readonly ? { readonly: true } : { readwrite: true, create: true };
}

const getOmpDir = () => path.join(os.homedir(), ".omp", "agent");
const getOmpDbPath = () => path.join(getOmpDir(), "agent.db");

export async function getOmpCredentials(providerId: string) {
  const dbPath = getOmpDbPath();
  try {
    const Database = await getDatabaseCtor();
    if (!Database) {
      return { hasOmniRoute: false, baseUrl: null, apiKey: null };
    }
    const db = new Database(dbPath, databaseOptions(true));
    const row = db
      .prepare(
        "SELECT data FROM auth_credentials WHERE provider = ? AND credential_type = 'api_key'"
      )
      .get(providerId) as { data: string } | undefined;
    db.close();

    if (row?.data) {
      const parsed = JSON.parse(row.data);
      return { hasOmniRoute: true, baseUrl: parsed.baseUrl || null, apiKey: parsed.apiKey || null };
    }
    return { hasOmniRoute: false, baseUrl: null, apiKey: null };
  } catch {
    return { hasOmniRoute: false, baseUrl: null, apiKey: null };
  }
}

export async function saveOmpCredentials(providerId: string, apiKey: string, baseUrl: string) {
  const dbPath = getOmpDbPath();
  const Database = await getDatabaseCtor();
  if (!Database) return;

  const db = new Database(dbPath, databaseOptions());

  db.prepare("DELETE FROM auth_credentials WHERE provider = ?").run(providerId);
  db.prepare(
    "INSERT INTO auth_credentials (provider, credential_type, data, disabled_cause, identity_key, created_at, updated_at) VALUES (?, ?, ?, NULL, NULL, ?, ?)"
  ).run(
    providerId,
    "api_key",
    JSON.stringify({ apiKey, baseUrl }),
    Math.floor(Date.now() / 1000),
    Math.floor(Date.now() / 1000)
  );

  db.close();
}

export async function deleteOmpCredentials(providerId: string) {
  const dbPath = getOmpDbPath();
  const Database = await getDatabaseCtor();
  if (!Database) return;

  const db = new Database(dbPath, databaseOptions());
  db.prepare("DELETE FROM auth_credentials WHERE provider = ?").run(providerId);
  db.close();
}
