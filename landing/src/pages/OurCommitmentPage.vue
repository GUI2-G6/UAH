<template>
  <main id="main-content" tabindex="-1">
    <section class="section-shell page-shell" aria-labelledby="commitment-heading">
      <div class="section-card page-card">
        <p class="section-label">Our Commitment</p>
        <h1 id="commitment-heading" class="page-title">Our Commitment to You</h1>
        <p class="section-intro">
          UAH is a student-built, open-source project in active beta. We do not treat trust copy as filler:
          this page reflects the standards we actively build toward and the constraints we still need to finish.
        </p>

        <div class="policy-grid">
          <article class="policy-card">
            <h2>What we always do</h2>
            <ul class="detail-list">
              <li>Keep optional features opt-in and transparent.</li>
              <li>Honor account deletion requests as real deletion.</li>
              <li>Maintain a clear path for data/privacy questions.</li>
              <li>Publish changes openly as behavior evolves.</li>
            </ul>
          </article>
          <article class="policy-card">
            <h2>What we never do</h2>
            <ul class="detail-list">
              <li>Sell user data.</li>
              <li>Use personal data for ad targeting.</li>
              <li>Hide data-handling changes in vague language.</li>
              <li>Ignore removal, correction, or privacy requests.</li>
            </ul>
          </article>
        </div>

        <article class="policy-card policy-card-wide">
          <h2>Current beta reality</h2>
          <p>
            Core account creation, job search, and application tracking are live. We still label in-progress work
            clearly, including parts of resume parsing and automation pathways that are under active iteration.
          </p>
          <p>
            Google sign-in is optional and works only after users explicitly link it from Settings on an existing
            account.
          </p>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Third-party services in use</h2>
          <p>
            We rely on a small set of infrastructure and provider integrations (for example DNS/security, geocoding,
            OAuth, and selected job data providers). Usage is disclosed so users can understand the stack while we
            keep private internals private.
          </p>
          <p>
            Detailed ecosystem distinctions are published on the <RouterLink to="/ecosystem">Ecosystem page</RouterLink>.
          </p>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Contact</h2>
          <p>
            <strong>Data &amp; privacy:</strong>
            <a href="mailto:privacy@uahapp.com">privacy@uahapp.com</a>
          </p>
          <p>
            <strong>General:</strong>
            <a href="mailto:team@uahapp.com">team@uahapp.com</a>
          </p>
          <p>
            <strong>Legal notices:</strong>
            <a href="mailto:legal@uahapp.com">legal@uahapp.com</a>
          </p>
          <p>
            <strong>Accessibility:</strong>
            <a href="mailto:accessibility@uahapp.com">accessibility@uahapp.com</a>
          </p>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>
