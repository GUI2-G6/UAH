<template>
  <main id="main-content" tabindex="-1">
    <section class="section-shell page-shell" aria-labelledby="commitment-heading">
      <div class="section-card page-card">
        <p class="section-label">Privacy Policy</p>
        <h1 id="commitment-heading" class="page-title">UAH Privacy Policy</h1>
        <p class="section-intro">
          UAH is a student-built, open-source project in active beta. This page explains what we collect, how we use
          it, and what controls you have.
        </p>

        <div class="policy-grid">
          <article class="policy-card">
            <h2>What we collect</h2>
            <ul class="detail-list">
              <li>Account data (email, username, password hash, profile basics).</li>
              <li>Resume and parsing data (uploaded PDF, extracted text, structured fields).</li>
              <li>Application tracking data (job, company, status, notes, session metadata).</li>
              <li>Optional Gmail connection data when you explicitly opt in.</li>
            </ul>
          </article>
          <article class="policy-card">
            <h2>What we never do</h2>
            <ul class="detail-list">
              <li>Sell user data.</li>
              <li>Share user data for advertising or data-broker purposes.</li>
              <li>Use personal data for ad targeting.</li>
              <li>Hide major data-handling changes behind vague copy.</li>
            </ul>
          </article>
        </div>

        <article class="policy-card policy-card-wide">
          <h2>How optional integrations work</h2>
          <p>
            Optional integrations stay opt-in. For Gmail, UAH uses read-only access and stores an encrypted refresh
            token while connected. Disconnecting Gmail removes stored token/email metadata in UAH and attempts Google
            token revocation.
          </p>
          <p>
            If Gmail is not connected, UAH does not access your mailbox.
          </p>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Cloud Parse status and phase-out direction</h2>
          <p>
            UAH supports Rules-based, Local AI, and Cloud AI resume parsing. Local AI and Rules-based parsing are the
            preferred direction. Cloud Parse is explicit opt-in today and is being phased out over time.
          </p>
          <p>
            Important: if you choose Cloud AI parsing, resume content is sent to external cloud AI endpoints for OCR
            and structured parsing.
          </p>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Third-party services and infrastructure</h2>
          <p>
            UAH uses a small provider set to run core functionality, including Google OAuth/Gmail (optional), cloud or
            local AI parsing paths, and core app infrastructure (database, queueing, and account email delivery).
          </p>
          <p>
            You can review broader provider context on the <RouterLink to="/ecosystem">Ecosystem page</RouterLink>.
          </p>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Your controls</h2>
          <ul class="detail-list">
            <li>Disconnect Gmail in Settings at any time.</li>
            <li>Delete uploaded resumes.</li>
            <li>Export your stored account data as a ZIP of CSV files after re-authentication.</li>
            <li>Delete your account.</li>
            <li>Contact us for privacy requests or corrections.</li>
          </ul>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Canonical policy document</h2>
          <p>
            This public page is paired with the repository policy document:
            <a href="https://github.com/GUI2-G6/UAH/blob/dev/PRIVACY.md" target="_blank" rel="noopener noreferrer">PRIVACY.md</a>.
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
