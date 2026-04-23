<template>
  <main id="main-content" tabindex="-1">
    <section class="section-shell page-shell" aria-labelledby="extension-heading">
      <div class="section-card page-card">
        <p class="section-label">Browser Extension</p>
        <h1 id="extension-heading" class="page-title">UAH Browser Extension (highly alpha)</h1>
        <p class="section-intro">
          The extension is in a highly alpha state with very limited functionality today. It should be treated as an
          early testing surface, not a finished product.
        </p>

        <article class="policy-card policy-card-wide">
          <h2>Current state</h2>
          <ul class="detail-list">
            <li>Chrome-first MV3 extension that signs in against your existing UAH account.</li>
            <li>Provides read-only snapshots for account, profile, and resume data.</li>
            <li>Includes a pinned panel plus manual <strong>Scan page</strong> and <strong>Fill page</strong> actions.</li>
            <li>Autofill is still early and intentionally limited to explicit user-triggered runs.</li>
          </ul>
        </article>

        <div class="policy-grid">
          <article class="policy-card">
            <h2>Download alpha build</h2>
            <p>
              Download the latest alpha zip package. This is a manually refreshed build and may lag behind the newest
              source commits.
            </p>
            <p>
              <a href="/downloads/uah-browser-extension-alpha.zip" download>Download uah-browser-extension-alpha.zip</a>
            </p>
          </article>
          <article class="policy-card">
            <h2>Install and repack guide</h2>
            <p>
              Follow the guide for building, repacking, and loading the extension in Chrome.
            </p>
            <p>
              <a
                href="/docs/BROWSER_EXTENSION_CHROME_INSTALL.md"
                target="_blank"
                rel="noopener noreferrer"
              >
                Open Chrome install guide (site-hosted)
              </a>
            </p>
            <p>
              <a
                href="https://github.com/GUI2-G6/UAH/blob/dev/docs/BROWSER_EXTENSION_CHROME_INSTALL.md"
                target="_blank"
                rel="noopener noreferrer"
              >
                Open Chrome install guide on GitHub
              </a>
            </p>
          </article>
        </div>

        <article class="policy-card policy-card-wide">
          <h2>Security and usage posture</h2>
          <p>
            This extension is scoped to UAH origins, uses explicit permissions for storage/cookies/tab scripting, and
            is designed around manual user actions. Review the extension security model before broader distribution.
          </p>
          <p>
            <a
              href="/docs/UAH_BROWSER_EXTENSION_SECURITY.md"
              target="_blank"
              rel="noopener noreferrer"
            >
              Read extension security model (site-hosted)
            </a>
          </p>
          <p>
            <a
              href="https://github.com/GUI2-G6/UAH/blob/dev/uah-browser-extension/SECURITY.md"
              target="_blank"
              rel="noopener noreferrer"
            >
              Read extension security model on GitHub
            </a>
          </p>
        </article>
      </div>
    </section>
  </main>
</template>
