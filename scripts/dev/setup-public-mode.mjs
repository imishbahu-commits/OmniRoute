#!/usr/bin/env node
/**
 * setup-public-mode.mjs — turn OFF the dashboard login on a running instance.
 *
 * Waits for the server to answer, signs in with the bootstrap password, then
 * PATCHes `requireLogin: false` so anyone with the link can open the dashboard
 * without a password. Idempotent: re-running when login is already disabled is
 * a no-op success.
 *
 * Usage:
 *   node scripts/dev/setup-public-mode.mjs
 *   node scripts/dev/setup-public-mode.mjs --password mypass --timeout 300
 *   node scripts/dev/setup-public-mode.mjs --lock      # put the login BACK on
 *
 * ⚠️  Public mode exposes provider credentials and quota to anyone with the URL.
 */

import process from "node:process";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}
const flag = (name) => process.argv.includes(`--${name}`);

const port = Number(arg("port", process.env.PORT || 20128));
const base = arg("base", `http://127.0.0.1:${port}`);
const password = arg("password", process.env.INITIAL_PASSWORD || "CHANGEME");
const timeoutSec = Number(arg("timeout", 300));
const lock = flag("lock");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Poll a cheap public endpoint until the server is answering. */
async function waitForServer() {
  const deadline = Date.now() + timeoutSec * 1000;
  let notified = false;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${base}/v1/models`, {
        signal: AbortSignal.timeout(10_000),
      });
      if (res.ok || res.status === 401) return true;
    } catch {
      /* not up yet */
    }
    if (!notified) {
      console.log("⏳ Waiting for OmniRoute to finish starting...");
      notified = true;
    }
    await sleep(2000);
  }
  return false;
}

/** True when the management API answers anonymously (login already disabled). */
async function loginDisabled() {
  try {
    const res = await fetch(`${base}/api/settings`, {
      signal: AbortSignal.timeout(15_000),
    });
    return res.status === 200;
  } catch {
    return false;
  }
}

async function main() {
  if (!(await waitForServer())) {
    console.error(`✖ OmniRoute did not respond on ${base} within ${timeoutSec}s.`);
    process.exit(1);
  }

  const alreadyOpen = await loginDisabled();
  if (!lock && alreadyOpen) {
    console.log("✓ Login is already disabled — nothing to do.");
    return;
  }

  // Sign in for the session cookie. When login is already disabled the cookie
  // is unnecessary but harmless, which keeps the --lock path working too.
  const loginRes = await fetch(`${base}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
    signal: AbortSignal.timeout(30_000),
  });

  const cookie = (loginRes.headers.getSetCookie?.() || []).map((c) => c.split(";")[0]).join("; ");

  if (!loginRes.ok && !alreadyOpen) {
    console.error(
      `✖ Login failed (HTTP ${loginRes.status}).\n` +
        `  Tried password: ${JSON.stringify(password)}\n` +
        `  Set the right one with --password <pw> or INITIAL_PASSWORD in .env.`
    );
    process.exit(1);
  }

  // `requireLogin` is security-impacting, so the API demands currentPassword.
  const res = await fetch(`${base}/api/settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...(cookie ? { cookie } : {}) },
    body: JSON.stringify({ requireLogin: lock, currentPassword: password }),
    signal: AbortSignal.timeout(60_000),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    console.error(`✖ Could not update settings (HTTP ${res.status}). ${body.slice(0, 300)}`);
    process.exit(1);
  }

  if (lock) {
    console.log("🔒 Login is ON again — the dashboard now requires the password.");
    return;
  }

  const open = await loginDisabled();
  console.log(
    open
      ? "✓ Public mode ON — the dashboard opens with no password."
      : "⚠ Settings saved, but the dashboard still wants a login. Restart the server and re-run."
  );
  if (!open) process.exit(1);
}

await main();
