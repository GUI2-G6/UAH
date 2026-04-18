<!-- Renders the hero, preserving the existing SVG wordmark and card illustration while updating the copy. -->
<template>
  <section class="hero" id="top" tabindex="-1">
    <div class="section-shell">
      <div class="hero-layout">
        <div class="hero-copy">
          <ul class="hero-tags" aria-label="UAH facts">
            <li>Open source</li>
            <li>Free forever</li>
            <li>Beta live now</li>
          </ul>

          <div class="hero-mark">
            <svg viewBox="0 0 620 160" role="img" aria-labelledby="uah-logo-title uah-logo-desc">
              <title id="uah-logo-title">UAH wordmark</title>
              <desc id="uah-logo-desc">Unified Application Hub wordmark.</desc>
              <defs>
                <linearGradient id="uah-fill" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#1F5C99"></stop>
                  <stop offset="100%" stop-color="#2D77BC"></stop>
                </linearGradient>
              </defs>
              <rect x="0" y="22" width="620" height="116" rx="34" fill="url(#uah-fill)"></rect>
              <rect x="24" y="0" width="132" height="26" rx="13" fill="#FF5757" opacity="0.9"></rect>
              <rect x="166" y="0" width="168" height="26" rx="13" fill="#9FD2F3" opacity="0.9"></rect>
              <rect x="344" y="0" width="124" height="26" rx="13" fill="#F6D9A6" opacity="0.95"></rect>
              <rect x="478" y="0" width="118" height="26" rx="13" fill="#F6C445" opacity="0.95"></rect>
              <text x="310" y="104" text-anchor="middle" font-size="92" font-weight="800" letter-spacing="10"
                fill="#FFFFFF" font-family="Inter, Arial, sans-serif">UAH</text>
            </svg>
          </div>

          <p class="hero-subtitle">Unified Application Hub</p>
          <h1>Your entire job search. One clean tool. No cost.</h1>
          <p class="hero-description">
            UAH brings job discovery and application tracking into a single, focused workspace — pulling from multiple
            job data sources, stripping out dead listings, and keeping your whole search organized in one place. We
            built what we needed and we're building it in the open. The beta is real and running, but it still has rough
            edges and a long way to go. If that sounds like something worth being part of, we want to hear from you.
          </p>

          <div class="hero-actions">
            <a class="button" href="#access">Request Beta Access</a>
            <a class="button-secondary" href="https://github.com/GUI2-G6/UAH" target="_blank"
              rel="noopener noreferrer">View on GitHub</a>
          </div>

          <p class="hero-note">
            Closed beta means exactly that: a working system, an unfinished product, and a small group of early testers
            helping decide what gets built next.
          </p>

          <a class="scroll-cue" href="#problem">
            <span class="scroll-cue-mark" aria-hidden="true">↓</span>
            <span>See why we built this</span>
          </a>
        </div>

        <div class="hero-visual" aria-hidden="true">
          <div class="visual-board">
            <div class="visual-orbit"></div>
            <div class="visual-card secondary">
              <span class="visual-chip"><span class="chip-dot"></span> Job discovery</span>
              <div class="visual-title">Normalized listings</div>
              <div class="fake-list">
                <span></span><span></span><span></span>
              </div>
            </div>
            <div class="visual-card tertiary">
              <span class="visual-chip"><span class="chip-dot" style="background:#F6C445;"></span> Freshness
                checks</span>
              <div class="metric-row">
                <div class="metric"><strong>Dead links</strong><span>Auto-removed</span></div>
                <div class="metric"><strong>Stale posts</strong><span>Auto-flagged</span></div>
              </div>
            </div>
            <div class="visual-card primary">
              <span class="visual-chip"><span class="chip-dot" style="background:#1F5C99;"></span> Unified
                workspace</span>
              <div class="visual-title">Search it. Track it. Follow up.</div>
              <div class="metric-row">
                <div class="metric"><strong>Search</strong><span>DB-backed filters</span></div>
                <div class="metric"><strong>Track</strong><span>Status, dates, notes</span></div>
              </div>
              <div class="fake-list" style="margin-top:18px;">
                <span style="width:100%;"></span>
                <span style="width:76%;"></span>
                <span style="width:92%;"></span>
              </div>
              <div class="visual-foot">
                <span class="visual-chip"><span class="status-dot"></span> Closed beta</span>
                <span>AI + cloud + rules parsing</span>
              </div>
            </div>
            <div class="visual-card quad">
              <span class="visual-chip"><span class="chip-dot" style="background:#FF5757;"></span> Application
                tracking</span>
              <div class="visual-title">Full history. Zero spreadsheets.</div>
              <div class="fake-list">
                <span style="width:100%;"></span>
                <span style="width:72%;"></span>
                <span style="width:58%;"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
