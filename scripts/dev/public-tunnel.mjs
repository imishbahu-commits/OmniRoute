#!/usr/bin/env node
/**
 * public-tunnel.mjs — expose a locally running OmniRoute instance on a public URL.
 *
 * Usage:
 *   node scripts/dev/public-tunnel.mjs                 # auto: ngrok if NGROK_AUTHTOKEN, else cloudflared
 *   node scripts/dev/public-tunnel.mjs --provider ngrok
 *   node scripts/dev/public-tunnel.mjs --provider cloudflare
 *   node scripts/dev/public-tunnel.mjs --port 20128
 *
 * Env:
 *   NGROK_AUTHTOKEN   ngrok authtoken (https://dashboard.ngrok.com/get-started/your-authtoken)
 *   PORT              local OmniRoute port (default 20128)
 *
 * After the tunnel is up the script prints the public base URL and patches
 * NEXT_PUBLIC_BASE_URL / OMNIROUTE_PUBLIC_BASE_URL hints so OAuth callbacks and
 * the dashboard build absolute links against the public origin.
 *
 * NOTE: requires outbound network access to the tunnel provider. Restricted /
 * TLS-intercepting networks (CI sandboxes, corporate MITM proxies) will fail the
 * provider handshake — run this from a machine with normal internet egress.
 */

import { spawn, execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import process from "node:process";

const HERE = path.dirname(fileURLToPath(import.meta.url));

/** Print a scannable QR for `url` by reusing the mobile-url renderer. */
function printQr(url) {
  try {
    const out = execFileSync(
      process.execPath,
      [path.join(HERE, "mobile-url.mjs"), "--qr-only", "--url", url],
      { encoding: "utf8" }
    );
    process.stdout.write(out);
  } catch {
    /* QR is a nicety — never fail the tunnel over it. */
  }
}

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

const port = Number(arg("port", process.env.PORT || 20128));
const requested = arg("provider", process.env.NGROK_AUTHTOKEN ? "ngrok" : "cloudflare");

function banner(url) {
  const line = "═".repeat(Math.max(38, url.length + 8));
  console.log(`\n${line}`);
  console.log(`  🌍  OmniRoute is PUBLIC at:`);
  console.log(`      ${url}`);
  console.log(`      Dashboard : ${url}/dashboard`);
  console.log(`      API base  : ${url}/v1`);
  console.log(`${line}`);
  console.log(`${line}`);
  console.log(`  📱  Scan with your phone camera to open it:`);
  printQr(url);
  console.log(`${line}`);
  console.log(`  Add to .env so links/OAuth use the public origin:`);
  console.log(`      NEXT_PUBLIC_BASE_URL=${url}`);
  console.log(`      OMNIROUTE_PUBLIC_BASE_URL=${url}`);
  console.log(`      AUTH_COOKIE_SECURE=true`);
  console.log(`${line}\n`);
}

async function viaNgrok() {
  const token = process.env.NGROK_AUTHTOKEN;
  if (!token) {
    console.error(
      "✖ NGROK_AUTHTOKEN is not set. Get one at https://dashboard.ngrok.com/get-started/your-authtoken"
    );
    process.exit(1);
  }
  const ngrok = await import("@ngrok/ngrok");
  const listener = await ngrok.forward({ addr: port, authtoken: token, proto: "http" });
  const url = listener.url();
  banner(url);
  process.stdin.resume();
  const stop = async () => {
    try {
      await listener.close();
    } catch {
      /* ignore */
    }
    process.exit(0);
  };
  process.on("SIGINT", stop);
  process.on("SIGTERM", stop);
}

function viaCloudflare() {
  const child = spawn(
    "cloudflared",
    ["tunnel", "--no-autoupdate", "--url", `http://localhost:${port}`],
    { stdio: ["ignore", "pipe", "pipe"] }
  );
  let printed = false;
  const scan = (buf) => {
    const text = buf.toString();
    process.stderr.write(text);
    const match = text.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/i);
    if (match && !printed) {
      printed = true;
      banner(match[0]);
    }
  };
  child.stdout.on("data", scan);
  child.stderr.on("data", scan);
  child.on("error", (err) => {
    if (err.code === "ENOENT") {
      console.error(
        "✖ cloudflared not found. Install it:\n" +
          "    brew install cloudflared            # macOS\n" +
          "    winget install Cloudflare.cloudflared  # Windows\n" +
          "    curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x cloudflared  # Linux"
      );
    } else {
      console.error(err);
    }
    process.exit(1);
  });
  child.on("exit", (code) => process.exit(code ?? 0));
}

console.log(`→ Exposing http://localhost:${port} via ${requested}...`);
if (requested === "ngrok") {
  await viaNgrok();
} else {
  viaCloudflare();
}
