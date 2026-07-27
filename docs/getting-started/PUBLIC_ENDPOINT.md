# Running OmniRoute as a Public Endpoint

How to run this repo locally and hand out a link that **anyone on the internet can open** — no login, no API key.

> ⚠️ **Security warning.** Public mode disables the dashboard login and the `/v1` API key
> requirement. Anyone with the link can read your provider credentials, spend your
> quota, and change settings. Only do this for demos/testing, on an instance with
> throwaway credentials, and tear the tunnel down when you're done.

---

## 1. Clone and install

```bash
git clone https://github.com/imishbahu-commits/OmniRoute.git
cd OmniRoute
npm install          # generates .env from .env.example and JWT/API secrets
```

Requires Node `>=22.22.2 <23 || >=24 <27` (see `.nvmrc`). Give the build
headroom — Next.js + Turbopack needs ~4 GB RAM free to compile the dashboard.

## 2. Run it

```bash
npm run dev          # dev server, http://0.0.0.0:20128
# or, for a faster/leaner runtime:
npm run build && npm start
```

Health check:

```bash
curl http://localhost:20128/v1/models
```

## 3. Make it public (no auth)

Public mode is already configured in `.env`:

| Key                             | Value            | Effect                                      |
| ------------------------------- | ---------------- | ------------------------------------------- |
| `HOST`                          | `0.0.0.0`        | Listen on all interfaces, not just loopback |
| `REQUIRE_API_KEY`               | `false`          | `/v1/*` accepts unauthenticated requests    |
| `CORS_ALLOWED_ORIGINS`          | `*`              | Any browser origin may call the API         |
| `LIVE_WS_HOST`                  | `0.0.0.0`        | Live dashboard WebSocket reachable remotely |
| `OMNIROUTE_ALLOWED_DEV_ORIGINS` | tunnel wildcards | Next.js accepts the tunnel hostname in dev  |

The dashboard login gate is a **database setting**, not an env var. Disable it once:

```bash
# log in with the password from INITIAL_PASSWORD in .env (default: CHANGEME)
curl -c cookies.txt -X POST http://localhost:20128/api/auth/login \
  -H 'Content-Type: application/json' -d '{"password":"CHANGEME"}'

# turn off requireLogin (security-impacting settings need the current password)
curl -b cookies.txt -X PATCH http://localhost:20128/api/settings \
  -H 'Content-Type: application/json' \
  -d '{"requireLogin":false,"currentPassword":"CHANGEME"}'
```

Verify anonymous access:

```bash
curl -o /dev/null -w '%{http_code}\n' http://localhost:20128/api/settings   # 200
curl -o /dev/null -w '%{http_code}\n' http://localhost:20128/v1/models      # 200
```

To re-lock later: `PATCH /api/settings` with `{"requireLogin":true,"currentPassword":"..."}`.

### What stays locked even in public mode

Routes that spawn child processes (`/api/services/*`, `/api/plugins/*`,
`/api/cli-tools/runtime/*`, `/api/mcp/*`, `/api/vnc-session/*`, …) are
loopback/LAN-only by design — see `src/server/authz/routeGuard.ts`. They return
`403 LOCAL_ONLY` over a tunnel. That's an RCE guard; don't remove it.

## 4. Get the public link

```bash
npm run public                     # auto-picks provider
npm run public:cloudflare          # https://<random>.trycloudflare.com  (no account)
NGROK_AUTHTOKEN=xxxxx npm run public:ngrok   # https://<random>.ngrok-free.app
```

The script prints the public URL plus the dashboard and `/v1` API base.

Install the agent first if needed:

```bash
# cloudflared
brew install cloudflared                                   # macOS
winget install Cloudflare.cloudflared                      # Windows
curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  && chmod +x cloudflared && sudo mv cloudflared /usr/local/bin/   # Linux

# ngrok token
# https://dashboard.ngrok.com/get-started/your-authtoken
```

### After the URL is live

Point absolute links/OAuth callbacks at the public origin and restart:

```dotenv
NEXT_PUBLIC_BASE_URL=https://<your-public-host>
OMNIROUTE_PUBLIC_BASE_URL=https://<your-public-host>
AUTH_COOKIE_SECURE=true
```

Share it:

```
https://<your-public-host>/dashboard      # UI
https://<your-public-host>/v1             # OpenAI-compatible API base
```

```bash
curl https://<your-public-host>/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"Hello!"}]}'
```

## 5. Tearing it down

Stop the tunnel (`Ctrl-C`), then restore auth:

```bash
curl -X PATCH http://localhost:20128/api/settings \
  -H 'Content-Type: application/json' \
  -d '{"requireLogin":true,"currentPassword":"CHANGEME"}'
```

and set `REQUIRE_API_KEY=true`, `CORS_ALLOWED_ORIGINS=` back in `.env`.

## Troubleshooting

| Symptom                                                  | Cause / fix                                                                                                                   |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `failed to connect session: tls handshake error` (ngrok) | Outbound TLS is intercepted by a corporate/CI proxy. Tunnels can't work there — run from an unrestricted network.             |
| `cloudflared` connects but page 404s                     | Wrong port — pass `--port <PORT>` matching `PORT` in `.env`.                                                                  |
| Dashboard compile hangs / OOM                            | Turbopack needs RAM. Use `NODE_OPTIONS=--max-old-space-size=2200 npm run dev`, or prebuild with `npm run build && npm start`. |
| `403 LOCAL_ONLY` on some API                             | Intentional loopback-only route (see above). Access it from the host machine.                                                 |
| Blocked `Cross origin request` warning in dev            | Add the tunnel host to `OMNIROUTE_ALLOWED_DEV_ORIGINS` in `.env`.                                                             |
