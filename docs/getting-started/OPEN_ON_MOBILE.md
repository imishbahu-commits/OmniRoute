# Open OmniRoute on Your Phone — Step by Step

Two ways. Pick one:

- **Way A — same Wi-Fi** (phone + computer on the same router). Easiest, 2 minutes.
- **Way B — anywhere** (mobile data, or share the link with a friend). Needs a free tunnel.

> ⚠️ Both ways assume public mode (no login, no API key). Anyone who has the link
> can use your AI providers and spend your quota. Use it for demos, then turn it
> off — see [Turning it off](#5-turning-it-off).

---

## 0. First: start OmniRoute on your computer

Do this once, in a terminal **on your computer** (not your phone):

```bash
git clone https://github.com/imishbahu-commits/OmniRoute.git
cd OmniRoute
npm install
npm run dev
```

Wait until you see:

```
[Next] dev server listening on http://0.0.0.0:20128
```

**Leave this terminal open.** If you close it, the phone link stops working.

> The first page load takes 1–3 minutes to compile — this is normal. Later loads are instant.

---

## Way A — Same Wi-Fi (easiest)

### Step 1 — Connect your phone to the same Wi-Fi as your computer

Not a different network, not mobile data. The **same** Wi-Fi name.

### Step 2 — Get your link

Open a **second terminal** (leave `npm run dev` running in the first) and run:

```bash
npm run mobile
```

You'll see something like:

```
══════════════════════════════════════════
  📱  OPEN THIS ON YOUR PHONE
══════════════════════════════════════════

  Dashboard : http://192.168.1.42:20128/dashboard
  API base  : http://192.168.1.42:20128/v1

  Scan with your phone camera:

  [ QR CODE ]
```

### Step 3 — Open it on your phone

**Either** point your phone's camera at the QR code and tap the notification,
**or** type the `Dashboard` address into your phone's browser by hand.

That's it — the dashboard loads, no password.

> `192.168.1.42` is an example. Use whatever number **your** terminal printed.

### If it doesn't load

| Problem                      | Fix                                                                                                                                              |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Page never loads / times out | Your computer's firewall is blocking it. See commands below.                                                                                     |
| "Can't reach this site"      | Phone is on a different Wi-Fi, or the Wi-Fi has "client isolation" / "AP isolation" on (common on guest and hotel Wi-Fi). Use **Way B** instead. |
| Several addresses printed    | Try each one — `npm run mobile` lists the alternates.                                                                                            |

Allow the port through the firewall:

```bash
# Windows (run PowerShell as Administrator)
netsh advfirewall firewall add rule name=OmniRoute dir=in action=allow protocol=TCP localport=20128

# Linux
sudo ufw allow 20128/tcp

# macOS — System Settings > Network > Firewall > Options > allow "node"
```

---

## Way B — From anywhere (mobile data, or share with others)

This gives you a real `https://…` internet link. Works on mobile data, on any
Wi-Fi, and you can send it to someone else.

### Step 1 — Install `cloudflared` (one time, free, no account)

```bash
# macOS
brew install cloudflared

# Windows
winget install Cloudflare.cloudflared

# Linux
curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared && sudo mv cloudflared /usr/local/bin/
```

### Step 2 — Start the tunnel

In a **second terminal** (keep `npm run dev` running in the first):

```bash
npm run public
```

### Step 3 — Open the link it prints

```
══════════════════════════════════════════
  🌍  OmniRoute is PUBLIC at:
      https://sunny-river-1234.trycloudflare.com
      Dashboard : https://sunny-river-1234.trycloudflare.com/dashboard
      API base  : https://sunny-river-1234.trycloudflare.com/v1
══════════════════════════════════════════
  📱  Scan with your phone camera to open it:

  [ QR CODE ]
```

Scan the QR with your phone, or send that link to anyone. It works from any
network on earth.

**Keep both terminals open** while you're using it. Closing the tunnel terminal
kills the link, and the URL changes every time you restart it.

### Prefer ngrok?

```bash
NGROK_AUTHTOKEN=your_token_here npm run public:ngrok
```

Get a free token at <https://dashboard.ngrok.com/get-started/your-authtoken>.

---

## 4. Once it's open on your phone

- **Dashboard** — `<link>/dashboard`: add providers, view usage, change settings.
- **API** — point any OpenAI-compatible app at `<link>/v1`:

```bash
curl <link>/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"Hello!"}]}'
```

**Add to home screen** for an app-like experience: it's a PWA.
Safari → Share → _Add to Home Screen_. Chrome → ⋮ → _Add to Home screen_.

> A few pages (embedded service UIs, plugins, MCP) show `403 LOCAL_ONLY` on your
> phone. That's a deliberate safety guard — those can run programs on your
> computer, so they only work from the computer itself.

---

## 5. Turning it off

Stop the tunnel and dev server with `Ctrl-C` in each terminal. Then put the
password back:

```bash
curl -X PATCH http://localhost:20128/api/settings \
  -H 'Content-Type: application/json' \
  -d '{"requireLogin":true,"currentPassword":"CHANGEME"}'
```

And in `.env`, set `REQUIRE_API_KEY=true` and clear `CORS_ALLOWED_ORIGINS`.

---

## Quick reference

| Command                         | What it does                           |
| ------------------------------- | -------------------------------------- |
| `npm run dev`                   | Start OmniRoute (leave running)        |
| `npm run mobile`                | Print Wi-Fi URL + QR for your phone    |
| `npm run public`                | Public internet URL + QR (cloudflared) |
| `npm run public:ngrok`          | Same, via ngrok                        |
| `npm run mobile -- --qr-only`   | Just the QR code                       |
| `npm run mobile -- --url <url>` | QR for any URL you pass                |

See also: [PUBLIC_ENDPOINT.md](./PUBLIC_ENDPOINT.md) for the full security details.
