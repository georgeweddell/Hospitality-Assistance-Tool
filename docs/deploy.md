# Deploying Docket on Render (step 11)

The live site is one Render **web service** built from the `Dockerfile`: it serves the React app and the API from one address, and keeps `auth.db` and `accounts/` on a **persistent disk** at `/data`. `render.yaml` describes it; Render reads that file when you create the service.

## One-off setup

1. **Push `main` to GitHub** (Render builds from GitHub, not from your laptop).
2. **Render account:** sign up at render.com, connect GitHub, and allow access to the `Hospitality-Assistance-Tool` repo.
3. **New → Blueprint**, pick the repo. Render reads `render.yaml` and shows one service, `docket`, with a 1 GB disk. It asks for the two values marked `sync: false`:
   - `ANTHROPIC_API_KEY`: from console.anthropic.com. Consider a separate key just for the live site, so you can revoke it on its own.
   - `INVITE_CODE`: any phrase; you need it to create your account. Anyone with it can sign up, so share it only with people you mean to.

   `SECRET_KEY` is made by Render (a new random value, not your laptop's). `DATA_DIR`, `COOKIE_SECURE`, `DEMO_ENABLED` and `API_DOCS` come from `render.yaml`.
4. **Apply.** The first build takes a few minutes. The **Logs** tab shows it; the last lines should include `account databases up to date` and `Uvicorn running`.
5. **Spend limit:** in the Anthropic console, set a monthly limit on the key.

## First visit

1. Open the `https://docket-….onrender.com` link from the Render dashboard.
2. **Create account** with your email, a password and the invite code.
3. For interviews: **Settings → reset → demo** loads the demo pizzeria into your account.

## Day to day

- **Updating:** push to `main` and Render rebuilds and redeploys by itself (a minute or two offline while the new version starts: a service with a disk stops the old one first). Accounts are safe on the disk.
- **Schema changes** reach the live accounts automatically: the start command runs `python migrate.py --all`.
- **Backups:** Render snapshots the disk every 24 hours and keeps each for at least 7 days (Disks section of the service).
- **If a deploy fails:** Logs tab. The previous version keeps running until a new one starts.

## Things to know

- **One instance only.** Login limits, open databases and running reports live in the server's memory, and a disk can only attach to one instance. Don't scale the service up to more instances.
- **Cost:** the `0.5c-512mb` plan plus a 1 GB disk (check Render's pricing page), and the Anthropic calls.
- **Try the demo is off** on the live site (`DEMO_ENABLED=0`). Setting it to `1` in the Render dashboard turns it back on; guests then use your Anthropic key (15 AI calls and 1 report each).
- **Checking locally first:** the `live-check` entry in `.claude/launch.json` runs the backend like the live site (its own data folder, demo off, port 8010) after `npm run build` in `frontend/`.
