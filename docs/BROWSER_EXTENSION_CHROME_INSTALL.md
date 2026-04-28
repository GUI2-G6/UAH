# UAH Browser Extension: Build, Repack, and Install in Chrome

The UAH browser extension is currently in a highly alpha state and has limited functionality. Use this guide for testing and internal evaluation, not broad production rollout.

## What works today (alpha scope)

- Existing UAH account sign-in (email/password and Google sign-in bridge).
- Read-only snapshots for account/profile/resume data in the popup UI.
- Manual `Scan page` and `Fill page` actions on the active tab.
- Pinned in-page panel for quick extension access.

For architecture and runtime details, see [`../uah-browser-extension/README.md`](../uah-browser-extension/README.md).

## Prerequisites

- Node.js: `^20.19.0 || >=22.12.0` (from [`../uah-browser-extension/package.json`](../uah-browser-extension/package.json)).
- npm installed with Node.js.
- Chrome or Chromium-based browser.

## 1) Configure extension environment

From the repo root:

```powershell
cd uah-browser-extension
copy .env.example .env
```

Edit `.env` for your target environment (for example beta):

```dotenv
VITE_EXTENSION_APP_ORIGIN=https://beta.uahapp.com
VITE_EXTENSION_API_ORIGIN=https://beta.uahapp.com
VITE_EXTENSION_AUTH_NAMESPACE=beta
```

The build enforces HTTPS origins and requires either `VITE_EXTENSION_AUTH_NAMESPACE` or `VITE_EXTENSION_AUTH_COOKIE_NAME`.

## 2) Build extension artifacts

```powershell
cd uah-browser-extension
npm ci
npm run build
```

Verify that `dist/manifest.json` exists after build.

## 3) Install in Chrome (recommended path)

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the `uah-browser-extension/dist` folder (not the repo root).

## 4) Repack/share as ZIP for testers

If you need to send the alpha build to someone else:

1. Zip the **contents** of `dist/` (not the parent folder).
2. Confirm `manifest.json` is at the ZIP root.
3. Receiver extracts ZIP to a folder.
4. Receiver loads that extracted folder through **Load unpacked**.

Important: Chrome does not directly install arbitrary ZIP files as signed extension packages.

## 5) Optional advanced path: Chrome “Pack extension”

Chrome can generate a packed extension (`.crx`) and private key (`.pem`) from an unpacked directory, but this is an advanced workflow.

- Keep the generated `.pem` private and secure.
- Do not commit private keys.
- For most internal testing, use **Load unpacked** instead.

## Refreshing the website download ZIP

The landing site points to `/downloads/uah-browser-extension-alpha.zip`. Refresh it whenever extension behavior changes:

1. Rebuild `uah-browser-extension/dist`.
2. Recreate ZIP from `dist` contents with `manifest.json` at the root.
3. Replace `landing/public/downloads/uah-browser-extension-alpha.zip`.
4. Commit the updated ZIP with any matching landing/docs text updates.
