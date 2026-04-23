# UAH Browser Extension: Build, Repack, and Install in Chrome

The UAH browser extension is currently in a highly alpha state with limited functionality. Use this guide for testing and internal evaluation.

## What works today (alpha scope)

- Existing UAH account sign-in (email/password and Google sign-in bridge)
- Read-only snapshots for account/profile/resume data in the popup
- Manual `Scan page` and `Fill page` actions on the active tab
- Pinned in-page panel for quick extension access

For architecture and runtime details, see:
https://github.com/GUI2-G6/UAH/blob/main/uah-browser-extension/README.md

## Prerequisites

- Node.js: `^20.19.0 || >=22.12.0`
- npm
- Chrome or a Chromium-based browser

## 1) Configure extension environment

From the repo root:

```powershell
cd uah-browser-extension
copy .env.example .env
```

Edit `.env`:

```dotenv
VITE_EXTENSION_APP_ORIGIN=https://beta.uahapp.com
VITE_EXTENSION_API_ORIGIN=https://beta.uahapp.com
VITE_EXTENSION_AUTH_NAMESPACE=beta
```

## 2) Build extension artifacts

```powershell
cd uah-browser-extension
npm ci
npm run build
```

Verify that `dist/manifest.json` exists.

## 3) Install in Chrome (recommended path)

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select `uah-browser-extension/dist`.

## 4) Repack/share as ZIP for testers

1. Zip the **contents** of `dist/` (not the parent folder).
2. Confirm `manifest.json` is at ZIP root.
3. Receiver extracts ZIP to a folder.
4. Receiver uses **Load unpacked** on that extracted folder.

Chrome does not directly install arbitrary ZIP files as signed extension packages.

## 5) Optional advanced path: Chrome "Pack extension"

Chrome can generate a packed extension (`.crx`) and private key (`.pem`) from an unpacked directory.

- Keep `.pem` private and secure.
- Never commit private keys.
- For internal testing, prefer **Load unpacked**.

## Refreshing website download ZIP

The landing site points to `/downloads/uah-browser-extension-alpha.zip`. Refresh it when extension behavior changes:

1. Rebuild `uah-browser-extension/dist`.
2. Recreate ZIP from `dist` contents with `manifest.json` at root.
3. Replace `landing/public/downloads/uah-browser-extension-alpha.zip`.
