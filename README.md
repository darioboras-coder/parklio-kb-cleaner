# Deploying the KB Cleaner to Streamlit Community Cloud

This is a step-by-step guide for deploying the Parklio Knowledge Base Cleaner
as a free public web app. The end result is a URL like
`https://parklio-kb-cleaner.streamlit.app` that your team can bookmark and
use from any browser, on desktop or mobile, without installing anything.

**Total time:** about 15 minutes the first time. After that, deployment is
automatic — push a change to GitHub and the app updates itself.

---

## What you'll need

- A **GitHub account** (free — sign up at github.com if you don't have one)
- A **Streamlit Community Cloud account** (free — sign up at share.streamlit.io)
- The three files in this folder:
  - `streamlit_app.py`
  - `requirements.txt`
  - `README.md` (this file — optional but recommended)

---

## Step 1 — Create a GitHub repository

1. Go to **github.com** and sign in.
2. Click the **+** icon in the top-right corner → **New repository**.
3. Fill in:
   - **Repository name:** `parklio-kb-cleaner` (or whatever you prefer)
   - **Description:** "Cleans Zoho Desk KB CSV exports into English-only Q&A PDFs"
   - **Public** ✓ (Streamlit Community Cloud's free tier requires a public repo)
   - ✓ **Add a README file** (just so the repo isn't empty)
4. Click **Create repository**.

## Step 2 — Upload the app files

1. On your new repository's page, click **Add file** → **Upload files**.
2. Drag in **all three files**:
   - `streamlit_app.py`
   - `requirements.txt`
   - `README.md`
3. Scroll down, leave the commit message as-is, click **Commit changes**.

Your repo should now show all three files at the root level. That's all GitHub
needs.

## Step 3 — Connect Streamlit Community Cloud

1. Go to **share.streamlit.io** and click **Sign in** → **Continue with GitHub**.
2. Authorize Streamlit to access your GitHub account when prompted.
3. Once signed in, click **Create app** (top-right corner).
4. Choose **Deploy a public app from GitHub**.
5. Fill in:
   - **Repository:** `your-username/parklio-kb-cleaner`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **App URL:** pick something like `parklio-kb-cleaner` — this becomes
     `https://parklio-kb-cleaner.streamlit.app`
6. Click **Deploy**.

Streamlit will now install the dependencies from `requirements.txt` and start
the app. **First deploy takes 2–5 minutes.** You'll see a build log; when it's
done, the app loads automatically.

## Step 4 — Share the URL with your team

Send your team the app URL. That's it. They open the link, drag in their CSV,
click **Process file**, and download the PDF. No accounts, no installs.

---

## Updating the app later

When you (or I) need to change something — tweak the language threshold, add
a column, change the styling — you don't redeploy. You just:

1. Edit `streamlit_app.py` directly on GitHub (click the file, click the pencil
   icon, edit, **Commit changes**).
2. Streamlit Community Cloud automatically detects the change and redeploys
   the app within 30 seconds.

That's the whole update workflow.

---

## Things that might go wrong

**Build fails with "ModuleNotFoundError"** — `requirements.txt` is missing or
misnamed. It must be at the repo root and spelled exactly `requirements.txt`.

**App loads but says "Error reading CSV"** — the uploaded CSV doesn't have an
`Article Title` and `Answer` column. Check the Zoho Desk export settings.

**App goes to sleep after a week of inactivity** — Streamlit Community Cloud
puts free apps to sleep after 7 days of no traffic. Anyone visiting the URL
wakes it up automatically (takes ~30 seconds on first wake). If your team uses
it weekly this never matters; if monthly, expect a small wait on the first run.

**Resource limits** — Community Cloud gives you 1 GB RAM. The Parklio KB at
~1100 rows uses well under that. If the KB ever grows past ~50,000 rows, you'd
need a paid tier or a different host — but that's many years away.

---

## What this app does NOT do

- It does not store your CSV. Files live in the user's browser session and are
  discarded when the tab closes.
- It does not log who uses it or what they upload.
- It does not need API keys, secrets, or environment variables.

If your KB ever contains sensitive content and you want a private app instead,
let me know and I'll add password protection (it's about 10 lines of extra
code).
