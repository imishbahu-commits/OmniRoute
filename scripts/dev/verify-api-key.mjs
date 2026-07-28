#!/usr/bin/env node
/**
 * verify-api-key.mjs — check whether an OmniRoute API key is valid.
 *
 * Two independent checks:
 *   1. FORMAT  (offline) — does the key match the shape OmniRoute mints?
 *                          Mirrors src/shared/utils/apiKey.ts::parseApiKey.
 *   2. LIVE    (network) — does a running OmniRoute instance accept it?
 *                          Sends `Authorization: Bearer <key>` to /v1/models.
 *
 * Usage:
 *   node scripts/dev/verify-api-key.mjs <api-key>
 *   node scripts/dev/verify-api-key.mjs <api-key> --base-url http://localhost:20128
 *   node scripts/dev/verify-api-key.mjs <api-key> --format-only
 *
 * Env:
 *   OMNIROUTE_BASE_URL  base URL of the instance (default http://localhost:20128)
 *   API_KEY_SECRET      required for the CRC check on `sk-<machine>-<id>-<crc>` keys.
 *                       Must be the SAME secret the instance used to mint the key,
 *                       otherwise a genuine key will fail the CRC step.
 *
 * Exit codes: 0 = accepted by the live instance (or format OK in --format-only)
 *             1 = rejected / malformed
 *             2 = could not reach the instance (verdict unknown)
 */

import crypto from "node:crypto";
import process from "node:process";

const DEFAULT_BASE_URL = process.env.OMNIROUTE_BASE_URL || "http://localhost:20128";
const PROBE_PATH = "/v1/models";
const PROBE_TIMEOUT_MS = 10_000;

function parseArgs(argv) {
  const args = { key: null, baseUrl: DEFAULT_BASE_URL, formatOnly: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--base-url") args.baseUrl = argv[++i];
    else if (a === "--format-only") args.formatOnly = true;
    else if (a === "-h" || a === "--help") args.help = true;
    else if (!a.startsWith("-") && args.key === null) args.key = a;
  }
  return args;
}

/** HMAC/pbkdf2 CRC, identical to src/shared/utils/apiKey.ts::generateCrc. */
function generateCrc(machineId, keyId, secret) {
  return crypto
    .pbkdf2Sync(machineId + keyId, secret, 1000, 32, "sha256")
    .toString("hex")
    .slice(0, 8);
}

/**
 * Offline shape check. Returns { ok, format, detail }.
 * OmniRoute mints keys as `sk-{machineId}-{keyId}-{crc8}`; a legacy
 * `sk-{random}` two-part form is also still accepted by the parser.
 */
function checkFormat(key, secret) {
  if (!key || typeof key !== "string") {
    return { ok: false, format: "none", detail: "empty or non-string key" };
  }
  if (!key.startsWith("sk-")) {
    return {
      ok: false,
      format: "unknown",
      detail: `key must start with "sk-" — got prefix "${key.slice(0, Math.min(8, key.length))}…"`,
    };
  }

  const parts = key.split("-");

  if (parts.length === 4) {
    const [, machineId, keyId, crc] = parts;
    if (!secret) {
      return {
        ok: null,
        format: "sk-machine (4-part)",
        detail: "shape is correct, but API_KEY_SECRET is unset so the CRC could not be verified",
      };
    }
    const expected = generateCrc(machineId, keyId, secret);
    if (crc !== expected) {
      return {
        ok: false,
        format: "sk-machine (4-part)",
        detail: `CRC mismatch (got ${crc}, expected ${expected} for this API_KEY_SECRET)`,
      };
    }
    return {
      ok: true,
      format: "sk-machine (4-part)",
      detail: `machineId=${machineId} keyId=${keyId} crc=OK`,
    };
  }

  if (parts.length === 2) {
    return { ok: true, format: "sk-legacy (2-part)", detail: `keyId=${parts[1]}` };
  }

  return {
    ok: false,
    format: "unknown",
    detail: `expected 2 or 4 dash-separated segments, got ${parts.length}`,
  };
}

/** Live probe: ask a running instance whether it accepts the key. */
async function probeLive(key, baseUrl) {
  const url = `${String(baseUrl).replace(/\/+$/, "")}${PROBE_PATH}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      method: "GET",
      headers: { Authorization: `Bearer ${key}`, Accept: "application/json" },
      signal: controller.signal,
    });
    const body = await res.text();
    return { reached: true, status: res.status, body: body.slice(0, 400), url };
  } catch (err) {
    return { reached: false, error: err?.message || String(err), url };
  } finally {
    clearTimeout(timer);
  }
}

function mask(key) {
  if (!key) return "(none)";
  if (key.length <= 10) return `${key.slice(0, 3)}***`;
  return `${key.slice(0, 6)}***${key.slice(-4)}`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.help || !args.key) {
    console.log(
      "Usage: node scripts/dev/verify-api-key.mjs <api-key> [--base-url URL] [--format-only]"
    );
    process.exit(args.help ? 0 : 1);
  }

  const secret = process.env.API_KEY_SECRET || null;

  console.log(`\nKey:      ${mask(args.key)}  (${args.key.length} chars)`);
  console.log(`Instance: ${args.baseUrl}${PROBE_PATH}\n`);

  // ---- 1. format -----------------------------------------------------------
  const fmt = checkFormat(args.key, secret);
  const fmtLabel = fmt.ok === true ? "PASS" : fmt.ok === null ? "INCONCLUSIVE" : "FAIL";
  console.log(`[1] FORMAT  ${fmtLabel}`);
  console.log(`    format: ${fmt.format}`);
  console.log(`    ${fmt.detail}`);

  if (args.formatOnly) {
    console.log();
    process.exit(fmt.ok === false ? 1 : 0);
  }

  // ---- 2. live -------------------------------------------------------------
  const live = await probeLive(args.key, args.baseUrl);
  console.log(`\n[2] LIVE`);

  if (!live.reached) {
    console.log(`    UNREACHABLE — ${live.error}`);
    console.log(`    Start OmniRoute (\`npm run dev\`) or pass --base-url, then re-run.`);
    console.log(`\nVERDICT: unknown — no instance answered.\n`);
    process.exit(2);
  }

  console.log(`    HTTP ${live.status}`);
  if (live.body) console.log(`    ${live.body.replace(/\n/g, "\n    ")}`);

  if (live.status === 200) {
    console.log(`\nVERDICT: VALID — the instance accepted this key.\n`);
    process.exit(0);
  }
  if (live.status === 401 || live.status === 403) {
    console.log(`\nVERDICT: INVALID — the instance rejected this key (${live.status}).\n`);
    process.exit(1);
  }
  console.log(`\nVERDICT: inconclusive — unexpected status ${live.status}.\n`);
  process.exit(2);
}

main().catch((err) => {
  console.error("verify-api-key failed:", err);
  process.exit(2);
});
