#!/usr/bin/env node
/**
 * mobile-url.mjs — print the URL to open OmniRoute on your phone.
 *
 * Usage:
 *   node scripts/dev/mobile-url.mjs            # Wi-Fi (LAN) URL + QR code
 *   node scripts/dev/mobile-url.mjs --qr-only
 *   node scripts/dev/mobile-url.mjs --url https://abc.trycloudflare.com
 *
 * Same Wi-Fi  -> use the LAN URL this prints.
 * Mobile data -> run `npm run public` first, then pass that https URL with --url.
 */

import { networkInterfaces } from "node:os";
import process from "node:process";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}
const has = (name) => process.argv.includes(`--${name}`);

const port = Number(arg("port", process.env.PORT || 20128));

/** Rank candidate LAN addresses so real Wi-Fi/Ethernet wins over virtual adapters. */
function score(name) {
  const n = name.toLowerCase();
  if (/^(wl|wlan|wi-?fi|en0|en1)/.test(n)) return 0;
  if (/^(eth|en|eno|ens|enp|ethernet)/.test(n)) return 1;
  if (/(docker|br-|veth|vmnet|vbox|virbr|utun|tun|tap|zt|tailscale|loopback)/.test(n)) return 9;
  return 5;
}

function lanAddresses() {
  const out = [];
  for (const [name, addrs] of Object.entries(networkInterfaces())) {
    for (const addr of addrs || []) {
      if (addr.family !== "IPv4" || addr.internal) continue;
      // 169.254.x.x is link-local (no real network) — never reachable from a phone.
      if (addr.address.startsWith("169.254.")) continue;
      out.push({ name, address: addr.address, priority: score(name) });
    }
  }
  return out.sort((a, b) => a.priority - b.priority);
}

/* ── Minimal QR encoder (byte mode, ECC L, auto version 1-10) ────────────── */
const GF_EXP = new Uint8Array(512);
const GF_LOG = new Uint8Array(256);
for (let i = 0, x = 1; i < 255; i++) {
  GF_EXP[i] = x;
  GF_LOG[x] = i;
  x <<= 1;
  if (x & 0x100) x ^= 0x11d;
}
for (let i = 255; i < 512; i++) GF_EXP[i] = GF_EXP[i - 255];
const gfMul = (a, b) => (a === 0 || b === 0 ? 0 : GF_EXP[GF_LOG[a] + GF_LOG[b]]);

function rsGenerator(degree) {
  let poly = [1];
  for (let i = 0; i < degree; i++) {
    const next = new Array(poly.length + 1).fill(0);
    for (let j = 0; j < poly.length; j++) {
      next[j] ^= gfMul(poly[j], 1);
      next[j + 1] ^= gfMul(poly[j], GF_EXP[i]);
    }
    poly = next;
  }
  return poly;
}

function rsEncode(data, ecLen) {
  const gen = rsGenerator(ecLen);
  const res = new Array(ecLen).fill(0);
  for (const byte of data) {
    const factor = byte ^ res[0];
    res.shift();
    res.push(0);
    for (let i = 0; i < ecLen; i++) res[i] ^= gfMul(gen[i + 1], factor);
  }
  return res;
}

// [version, totalCodewords, ecCodewordsPerBlock, blocks] for ECC level L.
// Capped at version 6: versions >= 7 additionally carry version-information
// blocks, which this minimal encoder does not emit. v6/L holds 136 data bytes —
// far more than any URL needs.
const VERSIONS = [
  [1, 26, 7, 1],
  [2, 44, 10, 1],
  [3, 70, 15, 1],
  [4, 100, 20, 1],
  [5, 134, 26, 1],
  [6, 172, 18, 2],
];
const ALIGN = {
  1: [],
  2: [6, 18],
  3: [6, 22],
  4: [6, 26],
  5: [6, 30],
  6: [6, 34],
};

function buildQr(text) {
  const bytes = [...Buffer.from(text, "utf8")];
  const spec = VERSIONS.find(([v, total, ec, blocks]) => {
    const dataCw = total - ec * blocks;
    const headerBits = 4 + (v < 10 ? 8 : 16);
    return dataCw * 8 >= headerBits + bytes.length * 8;
  });
  if (!spec) return null;
  const [version, totalCw, ecPerBlock, blocks] = spec;
  const dataCw = totalCw - ecPerBlock * blocks;

  const bits = [];
  const push = (val, len) => {
    for (let i = len - 1; i >= 0; i--) bits.push((val >> i) & 1);
  };
  push(0b0100, 4);
  push(bytes.length, version < 10 ? 8 : 16);
  for (const b of bytes) push(b, 8);
  for (let i = 0; i < 4 && bits.length < dataCw * 8; i++) bits.push(0);
  while (bits.length % 8) bits.push(0);
  const codewords = [];
  for (let i = 0; i < bits.length; i += 8)
    codewords.push(parseInt(bits.slice(i, i + 8).join(""), 2));
  const pad = [0xec, 0x11];
  for (let i = 0; codewords.length < dataCw; i++) codewords.push(pad[i % 2]);

  const perBlock = Math.floor(dataCw / blocks);
  const extra = dataCw % blocks;
  const dataBlocks = [];
  const ecBlocks = [];
  let offset = 0;
  for (let b = 0; b < blocks; b++) {
    const len = perBlock + (b >= blocks - extra ? 1 : 0);
    const chunk = codewords.slice(offset, offset + len);
    offset += len;
    dataBlocks.push(chunk);
    ecBlocks.push(rsEncode(chunk, ecPerBlock));
  }
  const interleaved = [];
  for (let i = 0; i < Math.max(...dataBlocks.map((d) => d.length)); i++)
    for (const blk of dataBlocks) if (i < blk.length) interleaved.push(blk[i]);
  for (let i = 0; i < ecPerBlock; i++) for (const blk of ecBlocks) interleaved.push(blk[i]);

  const size = version * 4 + 17;
  const mod = Array.from({ length: size }, () => new Array(size).fill(null));
  const setFinder = (r, c) => {
    for (let dr = -1; dr <= 7; dr++)
      for (let dc = -1; dc <= 7; dc++) {
        const rr = r + dr;
        const cc = c + dc;
        if (rr < 0 || rr >= size || cc < 0 || cc >= size) continue;
        const inner = dr >= 0 && dr <= 6 && dc >= 0 && dc <= 6;
        const on =
          inner &&
          (dr === 0 ||
            dr === 6 ||
            dc === 0 ||
            dc === 6 ||
            (dr >= 2 && dr <= 4 && dc >= 2 && dc <= 4));
        mod[rr][cc] = on ? 1 : 0;
      }
  };
  setFinder(0, 0);
  setFinder(0, size - 7);
  setFinder(size - 7, 0);
  const align = ALIGN[version];
  const last = align.length - 1;
  for (let ai = 0; ai < align.length; ai++)
    for (let bi = 0; bi < align.length; bi++) {
      // The three finder corners never carry an alignment pattern.
      if ((ai === 0 && bi === 0) || (ai === 0 && bi === last) || (ai === last && bi === 0))
        continue;
      const r = align[ai];
      const c = align[bi];
      for (let dr = -2; dr <= 2; dr++)
        for (let dc = -2; dc <= 2; dc++)
          mod[r + dr][c + dc] = Math.max(Math.abs(dr), Math.abs(dc)) !== 1 ? 1 : 0;
    }
  for (let i = 8; i < size - 8; i++) {
    if (mod[6][i] === null) mod[6][i] = i % 2 === 0 ? 1 : 0;
    if (mod[i][6] === null) mod[i][6] = i % 2 === 0 ? 1 : 0;
  }
  mod[size - 8][8] = 1;

  // Reserve the two format-information strips BEFORE laying data bits, or the
  // data stream gets written into them and the symbol becomes unscannable.
  const reserved = mod.map((row) => row.map((v) => v !== null));
  for (let i = 0; i <= 8; i++) {
    reserved[8][i] = true;
    reserved[i][8] = true;
  }
  for (let i = 0; i < 8; i++) {
    reserved[size - 1 - i][8] = true;
    reserved[8][size - 1 - i] = true;
  }
  const mask = (r, c) => (r + c) % 2 === 0; // mask pattern 0
  let bitIdx = 0;
  const allBits = [];
  for (const cw of interleaved) for (let i = 7; i >= 0; i--) allBits.push((cw >> i) & 1);
  let upward = true;
  for (let col = size - 1; col > 0; col -= 2) {
    if (col === 6) col--;
    const rows = upward ? [...Array(size).keys()].reverse() : [...Array(size).keys()];
    for (const row of rows)
      for (const c of [col, col - 1]) {
        if (reserved[row][c]) continue;
        let bit = bitIdx < allBits.length ? allBits[bitIdx++] : 0;
        if (mask(row, c)) bit ^= 1;
        mod[row][c] = bit;
      }
    upward = !upward;
  }

  // Format info: ECC L (01) + mask 0 (000), BCH-encoded and XOR-masked.
  const fmtData = 0b01000; // ECC level L (01) + mask pattern 0 (000)
  let rem = fmtData;
  for (let i = 0; i < 10; i++) rem = ((rem << 1) ^ (((rem >> 9) & 1) * 0x537)) & 0x3ff;
  const fmt = (((fmtData << 10) | rem) ^ 0x5412) & 0x7fff;
  const fmtBit = (i) => (fmt >> i) & 1; // bit 14 = MSB
  // Copy 1 — around the top-left finder.
  for (let i = 0; i <= 5; i++) mod[8][i] = fmtBit(14 - i);
  mod[8][7] = fmtBit(8);
  mod[8][8] = fmtBit(7);
  mod[7][8] = fmtBit(6);
  for (let i = 0; i <= 5; i++) mod[i][8] = fmtBit(i);
  // Copy 2 — below the top-right / right of the bottom-left finder.
  for (let i = 0; i <= 6; i++) mod[size - 1 - i][8] = fmtBit(14 - i);
  for (let j = 0; j <= 7; j++) mod[8][size - 8 + j] = fmtBit(7 - j);

  return mod.map((row) => row.map((v) => v ?? 0));
}

/**
 * Render as half-block glyphs with explicit ANSI colours. Colours are set
 * explicitly (rather than relying on the terminal's default fg/bg) so the
 * symbol stays scannable on light- AND dark-themed terminals — a plain-glyph
 * QR inverts and becomes unreadable on one of the two.
 */
function renderQr(text) {
  const m = buildQr(text);
  if (!m) return null;
  const size = m.length;
  const quiet = 4; // spec-mandated minimum quiet zone
  const at = (r, c) => (r < 0 || r >= size || c < 0 || c >= size ? 0 : m[r][c]);
  const FG_LIGHT = "\x1b[97m"; // bright white foreground
  const FG_DARK = "\x1b[30m"; // black foreground
  const BG_LIGHT = "\x1b[107m"; // bright white background
  const BG_DARK = "\x1b[40m"; // black background
  const RESET = "\x1b[0m";
  const lines = [];
  for (let r = -quiet; r < size + quiet; r += 2) {
    let line = "  ";
    let curFg = null;
    let curBg = null;
    for (let c = -quiet; c < size + quiet; c++) {
      // "▀" paints the upper half in the foreground colour and the lower half
      // in the background colour. A dark QR module must render dark.
      const fg = at(r, c) ? FG_DARK : FG_LIGHT;
      const bg = at(r + 1, c) ? BG_DARK : BG_LIGHT;
      // Only re-emit an escape when the colour actually changes.
      if (fg !== curFg) {
        line += fg;
        curFg = fg;
      }
      if (bg !== curBg) {
        line += bg;
        curBg = bg;
      }
      line += "▀";
    }
    lines.push(line + RESET);
  }
  return lines.join("\n");
}

/* ── Output ──────────────────────────────────────────────────────────────── */
const override = arg("url", null);
const candidates = lanAddresses();
const url = override || (candidates[0] ? `http://${candidates[0].address}:${port}` : null);

if (!url) {
  console.error(
    "✖ No LAN address found — this machine isn't on a normal Wi-Fi/Ethernet network.\n" +
      "  Run `npm run public` to get an internet URL instead, then:\n" +
      "     node scripts/dev/mobile-url.mjs --url https://<that-url>"
  );
  process.exit(1);
}

const qr = renderQr(url);

if (has("qr-only")) {
  if (qr) console.log(`\n${qr}\n`);
  console.log(`  ${url}\n`);
  process.exit(0);
}

const bar = "═".repeat(Math.max(46, url.length + 10));
console.log(`\n${bar}`);
console.log("  📱  OPEN THIS ON YOUR PHONE");
console.log(bar);
console.log(`\n  Dashboard : ${url}/dashboard`);
console.log(`  API base  : ${url}/v1\n`);
if (qr) {
  console.log("  Scan with your phone camera:\n");
  console.log(qr);
  console.log("");
}
console.log(bar);
if (!override) {
  console.log("  Phone must be on the SAME Wi-Fi as this computer.");
  console.log("  On mobile data instead?  ->  npm run public");
  if (candidates.length > 1) {
    console.log("\n  Other addresses to try if that one fails:");
    for (const c of candidates.slice(1))
      console.log(`    http://${c.address}:${port}   (${c.name})`);
  }
  console.log("\n  Not loading? Allow port " + port + " through your firewall:");
  console.log("    Windows : netsh advfirewall firewall add rule name=OmniRoute \\");
  console.log(`              dir=in action=allow protocol=TCP localport=${port}`);
  console.log(`    Linux   : sudo ufw allow ${port}/tcp`);
  console.log("    macOS   : System Settings > Network > Firewall > allow node");
}
console.log(bar + "\n");
