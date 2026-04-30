# Browser extension — documentation index

Canonical developer guides live in this folder and beside the extension package.

| Document | Purpose |
| --- | --- |
| [BROWSER_EXTENSION_CHROME_INSTALL.md](BROWSER_EXTENSION_CHROME_INSTALL.md) | Build, unpack, ZIP, Chrome install paths. |
| [../../uah-browser-extension/README.md](../../uah-browser-extension/README.md) | Runtime architecture, adapters, tests. |

## Static copies under `landing/public/docs/`

The marketing site ships markdown under [`landing/public/docs/`](../../landing/public/docs/) for direct browser access (for example `/docs/BROWSER_EXTENSION_CHROME_INSTALL.md`). Those files are **not** symlinked:

- After editing **`docs/extension/BROWSER_EXTENSION_CHROME_INSTALL.md`**, copy the revised body into **`landing/public/docs/BROWSER_EXTENSION_CHROME_INSTALL.md`**, preserving that copy’s GitHub-linked references where relative repo paths cannot resolve on static hosting.
- [BROWSER_EXTENSION_EASY_INSTALL.md](../../landing/public/docs/BROWSER_EXTENSION_EASY_INSTALL.md) and [UAH_BROWSER_EXTENSION_SECURITY.md](../../landing/public/docs/UAH_BROWSER_EXTENSION_SECURITY.md) live only under `landing/public/docs/` unless promoted into `docs/extension/` later.
