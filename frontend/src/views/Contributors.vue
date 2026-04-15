<template>
  <div class="contributors-page">
    <div class="contributors-container">
      <div class="page-header">
        <button class="back-btn" @click="goBack" type="button" aria-label="Go back">
          Back
        </button>
      </div>

      <header class="contributors-hero">
        <p class="eyebrow">Contributors</p>
        <h1>Built by people, credited permanently.</h1>
        <p class="hero-copy">
          UAH exists because of the people who built it. Everyone who has contributed is permanently
          credited here unless they personally ask us to remove them.
        </p>
      </header>

      <section class="contributors-section" aria-labelledby="founding-team-heading">
        <div class="section-heading">
          <p class="section-label">Tier 1</p>
          <h2 id="founding-team-heading">Founding Team</h2>
          <p class="section-copy">
            The core team that shaped the first version of UAH and the architecture underneath it.
          </p>
        </div>

        <div class="founders-grid">
          <article
            v-for="founder in founders"
            :key="founder.name"
            class="founder-card"
          >
            <div class="founder-card-top">
              <span class="founder-badge">Founder</span>
            </div>
            <div class="founder-header">
              <div class="founder-avatar" :style="{ '--avatar-tint': founder.tint }">
                {{ founder.initials }}
              </div>
              <div class="founder-meta">
                <h3>{{ founder.name }}</h3>
                <p>{{ founder.role }}</p>
              </div>
            </div>
            <p class="founder-blurb">{{ founder.blurb }}</p>
          </article>
        </div>
      </section>

      <section class="contributors-section" aria-labelledby="maintainers-heading">
        <div class="section-heading">
          <p class="section-label">Tier 2</p>
          <h2 id="maintainers-heading">Long-Term Maintainers</h2>
          <p class="section-copy">
            This section will be updated post-semester once long-term stewardship is finalized.
          </p>
        </div>

        <div class="empty-state-card">
          <p>Coming post-semester — anyone who wants to keep building is welcome.</p>
        </div>
      </section>

      <section class="contributors-section" aria-labelledby="community-heading">
        <div class="section-heading">
          <p class="section-label">Tier 3</p>
          <h2 id="community-heading">Community Contributors</h2>
          <p class="section-copy">
            Open source contributors with a merged PR can be listed here after reaching out to any
            long-term maintainer to introduce themselves.
          </p>
        </div>

        <div class="empty-state-card">
          <p>
            Be the first community contributor — check open issues on
            <a href="https://github.com/GUI2-G6/UAH" target="_blank" rel="noopener">GitHub</a>.
          </p>
        </div>
      </section>

      <section class="contribute-callout" aria-labelledby="contribute-heading">
        <h2 id="contribute-heading">Want to contribute?</h2>
        <p>
          UAH is open source and contributions of all kinds are welcome. The minimum bar for a
          community listing is a merged PR, and before being listed you should reach out to any LTS
          team member to introduce yourself.
        </p>
        <a class="repo-link" href="https://github.com/GUI2-G6/UAH" target="_blank" rel="noopener">
          github.com/GUI2-G6/UAH
        </a>
      </section>

      <p class="removal-note">
        Contributors are never removed unless they personally request it. The only exception is
        serious verified harm as described in the CLA.
      </p>

      <div class="page-footer">
        <button class="back-btn" @click="goBack" type="button" aria-label="Go back">
          Back
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { getCurrentUser } from '@/lib/auth'

const router = useRouter()

const founders = [
  {
    name: 'Trent Brown',
    role: 'Lead architect & infrastructure',
    blurb: 'Core systems design, infrastructure, project leadership, envisioned many of the things that make UAH unique.',
    initials: 'TB',
    tint: 'rgba(99, 102, 241, 0.18)',
  },
  {
    name: 'Nicholas',
    role: 'Design',
    blurb: 'Server icon set and frontend design contributions throughout the semester.',
    initials: 'N',
    tint: 'rgba(16, 185, 129, 0.18)',
  },
  {
    name: 'Elyas',
    role: 'Backend',
    blurb: 'Initial OAuth implementation and early job board endpoint work that helped shape the architecture.',
    initials: 'E',
    tint: 'rgba(249, 115, 22, 0.14)',
  },
  {
    name: 'Ram',
    role: 'Core team',
    blurb: 'Integral team member throughout the semester. Support, collaboration, and keeping things moving.',
    initials: 'R',
    tint: 'rgba(59, 130, 246, 0.16)',
  },
  {
    name: 'Rajin Kichannagari',
    role: 'Backend',
    blurb: 'Initial server auth and a solid chunk of the early backend endpoints.',
    initials: 'RK',
    tint: 'rgba(245, 158, 11, 0.16)',
  },
]

function hasSafeInAppHistory() {
  const previousEntry = window.history.state?.back
  return typeof previousEntry === 'string' && previousEntry.startsWith('/') && !previousEntry.startsWith('//')
}

function goBack() {
  if (hasSafeInAppHistory()) {
    router.back()
    return
  }

  router.push(getCurrentUser() ? '/home' : '/login')
}
</script>

<style scoped>
.contributors-page {
  min-height: 100%;
  padding: 48px 24px 64px;
  background: var(--app-page-background);
}

.contributors-container {
  width: min(1120px, 100%);
  margin: 0 auto;
}

.contributors-hero {
  margin-bottom: 40px;
}

.page-header,
.page-footer {
  display: flex;
}

.page-header {
  margin-bottom: 20px;
}

.page-footer {
  margin-top: 32px;
}

.eyebrow,
.section-label {
  margin: 0 0 8px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.78rem;
  font-weight: 700;
}

.contributors-hero h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3.2rem);
  letter-spacing: -0.03em;
  color: var(--color-text-primary);
}

.hero-copy,
.section-copy,
.founder-meta p,
.founder-blurb,
.empty-state-card,
.contribute-callout p,
.removal-note {
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.hero-copy {
  margin: 20px 0 0;
  max-width: 860px;
  font-size: 1.1rem;
}

.contributors-section {
  margin-top: 40px;
}

.back-btn {
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #111827;
  border-radius: 999px;
  padding: 10px 18px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.back-btn:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.back-btn:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.2);
  outline-offset: 2px;
}

.back-btn:active {
  transform: translateY(1px);
}

.section-heading {
  margin-bottom: 20px;
}

.section-heading h2,
.contribute-callout h2 {
  margin: 0;
  font-size: 1.55rem;
  color: var(--color-text-primary);
}

.section-copy {
  margin: 12px 0 0;
  max-width: 760px;
}

.founders-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.founder-card,
.empty-state-card,
.contribute-callout {
  border: 1px solid var(--border-color);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow-card);
  backdrop-filter: blur(10px);
}

.founder-card {
  padding: 20px;
}

.founder-card-top {
  margin-bottom: 16px;
}

.founder-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.88rem;
  font-weight: 700;
  color: #4338ca;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.16);
}

.founder-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.founder-avatar {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--avatar-tint);
  color: var(--color-text-primary);
  border: 1px solid rgba(148, 163, 184, 0.22);
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.founder-meta h3 {
  margin: 0;
  font-size: 1.35rem;
  color: var(--color-text-primary);
}

.founder-meta p {
  margin: 4px 0 0;
}

.founder-blurb {
  margin: 18px 0 0;
  padding-top: 18px;
  border-top: 1px solid var(--border-color-light);
}

.empty-state-card {
  padding: 22px 24px;
  font-style: italic;
}

.empty-state-card p {
  margin: 0;
}

.empty-state-card a,
.repo-link {
  color: var(--color-primary-600);
  text-decoration: none;
}

.empty-state-card a:hover,
.repo-link:hover {
  text-decoration: underline;
}

.contribute-callout {
  margin-top: 56px;
  padding: 28px 28px 30px;
}

.contribute-callout p {
  margin: 14px 0 0;
  max-width: 880px;
}

.repo-link {
  display: inline-flex;
  margin-top: 18px;
  font-weight: 700;
}

.removal-note {
  margin: 22px 0 0;
  max-width: 960px;
}

@media (max-width: 900px) {
  .founders-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .contributors-page {
    padding: 32px 16px 48px;
  }

  .founder-card,
  .empty-state-card,
  .contribute-callout {
    border-radius: 16px;
  }

  .founder-header {
    align-items: flex-start;
  }

  .founder-avatar {
    width: 54px;
    height: 54px;
    font-size: 1.05rem;
  }

  .contribute-callout {
    padding: 22px 20px 24px;
  }
}
</style>
