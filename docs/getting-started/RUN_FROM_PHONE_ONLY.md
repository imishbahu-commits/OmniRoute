# Run OmniRoute With ONLY a Phone (No Laptop)

You don't need a computer. GitHub gives every account a **free cloud computer**
(a "Codespace") that you control from your phone's browser. OmniRoute runs
there, and you get a link you can open in any phone browser.

**Free allowance:** 60 hours per month on the free plan (120 core-hours ÷ 2 cores).
Plenty for regular use. GitHub asks for a card only if you go beyond it.

> ⚠️ These steps turn OFF the password. Anyone with your link can use your AI
> providers and spend your quota. Don't post the link publicly, and stop the
> Codespace when you're done (Step 6).

---

## What you need

- A phone with a browser (Chrome or Safari, both fine)
- A free GitHub account — <https://github.com/signup>
- About 10 minutes for the first setup (later starts take ~1 minute)

---

## Step 1 — Open the repo on your phone

In your phone browser go to:

```
https://github.com/imishbahu-commits/OmniRoute
```

Sign in to GitHub if it asks.

## Step 2 — Create the Codespace

1. Tap the green **`< > Code`** button near the top.
2. Tap the **Codespaces** tab (next to "Local").
3. Tap **Create codespace on main**.

> 💡 **Tip:** rotate your phone to landscape. The editor is cramped in portrait.

A code editor now opens **in your phone's browser**. This is your cloud computer.

## Step 3 — Wait for it to set itself up

This repo is pre-configured, so setup runs on its own. You'll see it install
packages and start OmniRoute in a terminal panel at the bottom.

**The first time takes about 5–10 minutes.** Leave the tab open. Don't lock your
phone — some phones pause background tabs. If it goes quiet, tap the screen.

When it's ready you'll see, in the terminal:

```
✓ Port 20128 is public — anyone with the link can reach it.
✓ Public mode ON — the dashboard opens with no password.

════════════════════════════════════════════
  📱  OPEN THIS ON YOUR PHONE

  Dashboard : https://<your-name>-20128.app.github.dev/dashboard
```

## Step 4 — Open your link

**Tap and hold** the `Dashboard` link in the terminal to copy it, then paste it
into a new browser tab. Or use the **Ports** tab (see below) and tap the globe 🌐.

That's your OmniRoute. Bookmark it, or **Add to Home Screen** to make it behave
like a real app:

- **Safari** → Share → _Add to Home Screen_
- **Chrome** → ⋮ → _Add to Home screen_

## Step 5 — If the automatic setup didn't finish

Open the terminal panel in the editor (☰ menu → **Terminal** → **New Terminal**)
and type:

```bash
bash .devcontainer/start-public.sh
```

That re-runs everything and prints the link again. It's safe to run repeatedly.

## Step 6 — Stopping it (do this when you're done!)

The Codespace keeps burning your free hours while it runs.

1. Go to <https://github.com/codespaces>
2. Find yours, tap the **⋯** menu
3. Tap **Stop codespace**

Your data is kept. **Restarting later takes ~1 minute** — tap it, then run
`bash .devcontainer/start-public.sh` if it doesn't auto-start.

Tap **Delete** instead if you want it gone completely.

---

## Making the link private again

While it's running, in the terminal:

```bash
npm run public:lock
```

Now the dashboard asks for a password (`CHANGEME` by default — change it in
Settings). To open it back up: `npm run public:open`.

To stop strangers reaching the URL at all, set the port back to private:
**Ports** tab → long-press port `20128` → **Port Visibility** → **Private**.

---

## Troubleshooting

| What you see                         | What to do                                                                                           |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Link shows a GitHub sign-in page     | The port is still private. Terminal: `gh codespace ports visibility 20128:public -c $CODESPACE_NAME` |
| "502 Bad Gateway" or blank page      | Still compiling. Wait 2 minutes, then reload.                                                        |
| Terminal panel is missing            | ☰ menu → **Terminal** → **New Terminal**                                                            |
| Setup seems stuck                    | `bash .devcontainer/start-public.sh`                                                                 |
| Dashboard asks for a password        | `npm run public:open`                                                                                |
| Want to see what went wrong          | `tail -50 /tmp/omniroute.log`                                                                        |
| Codespace won't start / out of hours | Check <https://github.com/settings/billing>                                                          |

### Typing on a phone keyboard

The editor terminal is awkward on mobile. Tips:

- Long-press to paste; the ⌘/Ctrl row sits just above the keyboard.
- Commands here are short on purpose — `npm run public:open` is the longest.
- A cheap Bluetooth keyboard makes this dramatically nicer if you do it often.

---

## Other phone-friendly options

Codespaces is the simplest, but not the only way:

| Option                   | Cost         | Notes                                                                                                                    |
| ------------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------ |
| **GitHub Codespaces**    | Free 60 h/mo | What this guide covers. Easiest.                                                                                         |
| **Termux** (Android)     | Free         | Runs Node _on_ your phone. `pkg install nodejs git`, then clone and `npm install`. Slow, needs ~2 GB free, Android only. |
| **A cheap VPS**          | ~$5/mo       | Always-on, your own URL. Follow [PUBLIC_ENDPOINT.md](./PUBLIC_ENDPOINT.md) over SSH.                                     |
| **Docker host / Fly.io** | Varies       | `fly.toml` and `Dockerfile` are already in this repo.                                                                    |

---

## Quick reference

| Command                              | What it does                      |
| ------------------------------------ | --------------------------------- |
| `bash .devcontainer/start-public.sh` | Start everything + print the link |
| `npm run public:open`                | Turn the password OFF             |
| `npm run public:lock`                | Turn the password ON              |
| `npm run mobile -- --url <url>`      | Print a QR code for a link        |
| `tail -50 /tmp/omniroute.log`        | See the server log                |

See also: [OPEN_ON_MOBILE.md](./OPEN_ON_MOBILE.md) (if you also have a laptop)
and [PUBLIC_ENDPOINT.md](./PUBLIC_ENDPOINT.md) (security details).
