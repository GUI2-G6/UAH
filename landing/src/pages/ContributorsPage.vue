<template>
  <main id="main-content" tabindex="-1">
    <section class="section-shell page-shell" aria-labelledby="contributors-heading">
      <div class="section-card page-card">
        <p class="section-label">Contributors</p>
        <h1 id="contributors-heading" class="page-title">Built by people, credited permanently.</h1>
        <p class="section-intro">
          UAH exists because contributors shipped real work. Credits remain unless someone personally asks to be removed.
        </p>

        <div class="contributors-grid">
          <article class="contributor-card" v-for="person in founders" :key="person.name">
            <div class="contributor-head">
              <div class="contributor-avatar" :style="{ '--avatar-tint': person.tint }">{{ person.initials }}</div>
              <div>
                <h2>{{ person.name }}</h2>
                <p class="contributor-role">{{ person.role }}</p>
              </div>
            </div>
            <p>{{ person.blurb }}</p>
          </article>
        </div>

        <div class="policy-grid">
          <article class="policy-card">
            <h2>Long-term maintainers</h2>
            <p>This role is finalized post-semester based on stewardship and ongoing ownership.</p>
          </article>
          <article class="policy-card">
            <h2>Community contributors</h2>
            <p>
              Open source contributions are welcome. Merged PRs can be credited after maintainer confirmation.
            </p>
          </article>
        </div>

        <article class="policy-card policy-card-wide">
          <h2>Contribute</h2>
          <p>
            Browse issues and open pull requests at
            <a href="https://github.com/GUI2-G6/UAH" target="_blank" rel="noopener noreferrer">github.com/GUI2-G6/UAH</a>.
          </p>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
const founders = [
  {
    name: 'Trent Brown',
    role: 'Lead architect & infrastructure',
    blurb: 'Core systems design, project leadership, and long-range platform direction.',
    initials: 'TB',
    tint: 'rgba(99, 102, 241, 0.18)',
  },
  {
    name: 'Nicholas',
    role: 'Design',
    blurb: 'Iconography and frontend design contributions across the semester.',
    initials: 'N',
    tint: 'rgba(16, 185, 129, 0.18)',
  },
  {
    name: 'Elyas',
    role: 'Backend',
    blurb: 'Early OAuth and job-board endpoint contributions that shaped initial architecture.',
    initials: 'E',
    tint: 'rgba(249, 115, 22, 0.14)',
  },
  {
    name: 'Ram',
    role: 'Core team',
    blurb: 'Project support and cross-team coordination throughout active delivery.',
    initials: 'R',
    tint: 'rgba(59, 130, 246, 0.16)',
  },
  {
    name: 'Rajin Kichannagari',
    role: 'Backend',
    blurb: 'Initial server auth and a significant portion of the foundational backend endpoints.',
    initials: 'RK',
    tint: 'rgba(245, 158, 11, 0.16)',
  },
]
</script>
