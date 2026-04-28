<template>
  <main id="main-content" tabindex="-1">
    <section class="section-shell page-shell" aria-labelledby="terms-heading">
      <div class="section-card page-card">
        <p class="section-label">Terms of Service</p>
        <h1 id="terms-heading" class="page-title">UAH Terms of Service</h1>
        <p class="section-intro">
          These Terms explain the rules for using UAH in clear language. UAH is a student-built, open-source project
          in active beta.
        </p>

        <article class="policy-card policy-card-wide">
          <h2>TL;DR</h2>
          <ul class="detail-list">
            <li>We do not sell user data.</li>
            <li>We do not share user data for ad targeting or data-broker purposes.</li>
            <li>Use UAH lawfully and responsibly.</li>
            <li>UAH is a beta service and can evolve quickly.</li>
            <li>Disputes are contact-first and good-faith in this version of the Terms.</li>
          </ul>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Service scope and user responsibilities</h2>
          <p>
            UAH provides job-search and application workflow tools. You are responsible for account security and
            accurate information. You agree not to misuse the service, interfere with infrastructure, or violate laws.
          </p>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Transparency and ethics commitments</h2>
          <ul class="detail-list">
            <li>No sale of user data.</li>
            <li>No ad-targeting use of personal data.</li>
            <li>No deceptive or hidden data-policy behavior.</li>
            <li>Clear disclosure when material terms change.</li>
          </ul>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Privacy and data handling</h2>
          <p>
            Data handling details are described in the
            <RouterLink to="/our-commitment">Privacy Policy</RouterLink>.
            Optional integrations remain opt-in where applicable.
          </p>
          <p>
            You can manage data via account controls, including disconnecting integrations, deleting resumes, and
            deleting your account.
          </p>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Availability, warranty, and limitations</h2>
          <p>
            UAH is provided on an "as is" and "as available" basis. Because this is a beta project, features and
            availability may change. Liability is limited to the fullest extent allowed by law.
          </p>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Disputes (contact-first)</h2>
          <p>
            If you have a dispute or concern, contact us first so we can resolve it in good faith:
            <a href="mailto:legal@uahapp.com">legal@uahapp.com</a>
            or
            <a href="mailto:team@uahapp.com">team@uahapp.com</a>.
          </p>
          <p>This version of the Terms does not include a mandatory arbitration clause.</p>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Canonical terms document</h2>
          <p>
            This page is paired with the repository terms document:
            <a href="https://github.com/GUI2-G6/UAH/blob/dev/TERMS.md" target="_blank" rel="noopener noreferrer">TERMS.md</a>.
          </p>
          <p><strong>Last updated:</strong> 2026-04-28</p>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>
