<!-- Renders the infrastructure section and separates live beta realities from roadmap work. -->
<template>
  <section id="built" tabindex="-1">
    <div class="section-shell">
      <div class="section-card">
        <p class="section-label">Technical reality</p>
        <h2>Built on real infrastructure. Still very much a work in progress.</h2>
        <div class="build-layout">
          <div class="build-copy">
            <p>UAH runs today as a real deployed system: FastAPI on the backend, Vue 3 on the frontend, PostgreSQL for
              state, Redis for queueing, and Celery for background work. The beta environment lives on a personal
              Proxmox homelab with separate dev and beta deployment shapes, and beta access is gated through a
              Cloudflare tunnel with Zero Trust.</p>
            <p>The current beta already includes multi-provider job aggregation, automated staleness detection, dead-link
              removal, cross-provider deduplication, and a resume parsing pipeline that can use local Ollama, Z.AI cloud
              fallback, and rules-based extraction. GitHub Actions is also in place for build checks, backend
              syntax/lint checks, secret scanning, env sync checks, and dependency audits.</p>
            <p>Some of the things people ask for most are still part of the journey, not live promises: natural language
              search is still on the roadmap, broader provider coverage is still being evaluated beyond the current
              active/default-enabled set, public registration is not open, and the browser extension exists as an early
              surface that is still evolving.</p>
            <div class="build-actions">
              <a class="button-secondary" href="https://github.com/GUI2-G6/UAH" target="_blank"
                rel="noopener noreferrer">Read the full codebase</a>
            </div>
          </div>
          <aside class="build-sheet">
            <div>
              <strong>Live now</strong>
              <ul class="detail-list">
                <li>Proxmox-hosted dev and beta environments with Cloudflare Zero Trust in front of beta.</li>
                <li>Resume parsing through local Ollama, Z.AI cloud fallback, and rules-based extraction.</li>
                <li>Job aggregation with freshness checks, dead-link removal, and cross-provider deduplication.</li>
                <li>GitHub Actions checks for builds, syntax/lint, secret scanning, env sync, and dependency audits.</li>
              </ul>
            </div>
            <div>
              <strong>In progress</strong>
              <ul class="detail-list">
                <li>Natural language search is still in design, not a live beta capability yet.</li>
                <li>Additional provider integrations are being evaluated beyond the current active The Muse and
                  Arbeitnow set.</li>
                <li>The browser extension exists, but it is still an early surface and not something we present as
                  finished.</li>
                <li>Public access and open registration are still ahead of us, not available today.</li>
              </ul>
            </div>
          </aside>
        </div>
        <div class="tech-badges" aria-label="Tech stack">
          <span class="tech-badge">FastAPI</span>
          <span class="tech-badge">Vue 3</span>
          <span class="tech-badge">PostgreSQL</span>
          <span class="tech-badge">Redis</span>
          <span class="tech-badge">Celery</span>
          <span class="tech-badge">Proxmox</span>
          <span class="tech-badge">Cloudflare</span>
          <span class="tech-badge">Ollama</span>
          <span class="tech-badge">GitHub</span>
        </div>
      </div>
    </div>
  </section>
</template>
