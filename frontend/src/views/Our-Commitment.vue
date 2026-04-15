<template>
  <div class="commitment-page">
    <div class="commitment-container">
      <div class="page-header">
        <button class="back-btn" @click="goBack" type="button" aria-label="Go back">
          Back
        </button>
        <h1>Our Commitment to You</h1>
      </div>
      <p class="subtitle"><strong>UAH (Unified Application Hub)</strong></p>
      <p class="last-updated"><em>Last updated: April 15, 2026</em></p>

      <hr />

      <p>
        UAH is a student-built, not-for-profit, open source project. We're in active beta — learning,
        building, and figuring things out as we go. We don't have a legal team or a corporate privacy
        department. What we do have is a genuine commitment to doing right by the people who use this.
      </p>
      <p>
        This page is honest about where we are. A full, legally-reviewed privacy policy is coming —
        but we won't publish one until it accurately reflects how UAH actually works. In the meantime,
        we want you to know exactly what we stand for.
      </p>

      <hr />

      <h2>What We Will Always Do</h2>

      <p><strong>Be transparent.</strong><br />
      If something changes about how UAH handles your data, we'll tell you. We won't hide it in an
      update buried in a changelog nobody reads.</p>

      <p><strong>Give you control.</strong><br />
      Every optional feature is opt-in. You can use UAH without connecting your email, without the
      Vault, without resume parsing. Core functionality will never be gated behind data sharing.</p>

      <p><strong>Delete your data for real.</strong><br />
      If you ask us to delete your account, we mean it. Not a soft delete. Not "deactivated." Gone.</p>

      <p><strong>Let you take your data with you.</strong><br />
      We're building a full data export feature. When it's ready, everything UAH knows about you
      will be downloadable in one click.</p>

      <p><strong>Keep your credentials off our servers.</strong><br />
      The Vault is being designed so that your ATS passwords are architecturally incapable of reaching
      UAH's servers. This isn't a promise — it's a design constraint.</p>

      <hr />

      <h2>What We Will Never Do</h2>
      <ul>
        <li>Sell your data. To anyone. Ever.</li>
        <li>Use your data for advertising.</li>
        <li>Run advertising on UAH at all.</li>
        <li>Share your personal information with third parties for their benefit.</li>
        <li>Claim to do something we don't actually do.</li>
      </ul>

      <hr />

      <h2>Where We Are Right Now</h2>
      <p>
        We're in closed beta. The codebase is moving fast and some features described elsewhere are
        still being built. Here's an honest snapshot of what currently exists versus what's coming:
      </p>

      <table>
        <thead>
          <tr>
            <th>Feature</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>Account creation &amp; login</td><td>✓ Live</td></tr>
          <tr><td>Job search &amp; listing aggregation</td><td>✓ Live</td></tr>
          <tr><td>Application tracking</td><td>✓ Live</td></tr>
          <tr><td>Resume parsing (with Z.ai cloud fallback)</td><td>✓ Live (see note below)</td></tr>
          <tr><td>Gmail job update scanning</td><td>⚡ Partial — in development</td></tr>
          <tr><td>Dedicated apply address (@apply.uahapp.com)</td><td>🔜 Planned</td></tr>
          <tr><td>The Vault (local ATS status checker)</td><td>🔜 Planned</td></tr>
          <tr><td>Data export / takeout</td><td>🔜 Planned</td></tr>
          <tr><td>Full legal privacy policy</td><td>🔜 In progress</td></tr>
        </tbody>
      </table>

      <hr />

      <h2>A Note on Resume Parsing</h2>
      <p>
        Resume parsing currently uses the Z.ai API as a temporary cloud fallback. Your resume content
        is processed in real-time by Z.ai (Singapore-based) and not retained by them per their Data
        Processing Addendum. UAH stores your resume file and parsed output on our own servers to avoid
        re-processing.
      </p>
      <p>
        This is not our preferred architecture. Our goal is fully local inference — running AI models
        on our own hardware so resume content never leaves our infrastructure. We're upgrading our
        server GPU to make this possible (targeting summer 2026). When that happens, this note goes away.
      </p>
      <p>
        If you're not comfortable with cloud processing of your resume right now, you can use manual
        entry instead. Resume parsing is entirely optional.
      </p>

      <hr />

      <h2>Third Parties We Currently Use</h2>
      <p>
        We use a small number of external services to operate UAH. We don't get paid to use them and
        we don't share your personal data with them for their benefit.
      </p>

      <table>
        <thead>
          <tr>
            <th>Service</th>
            <th>What For</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Cloudflare</strong></td>
            <td>Infrastructure, security, DNS</td>
            <td>Sees IP addresses and request metadata</td>
          </tr>
          <tr>
            <td><strong>Google OAuth</strong></td>
            <td>Optional login and Gmail scanning</td>
            <td>Email address and OAuth token if you connect</td>
          </tr>
          <tr>
            <td><strong>Z.ai API</strong></td>
            <td>Resume parsing (temporary)</td>
            <td>Resume content, real-time only, not stored by them</td>
          </tr>
          <tr>
            <td><strong>ip-api / ipstack</strong></td>
            <td>IP-based location for job search</td>
            <td>Used for approximate location only, not stored</td>
          </tr>
          <tr>
            <td><strong>Nominatim / GeoNames</strong></td>
            <td>Geocoding for location search</td>
            <td>No personal data sent</td>
          </tr>
          <tr>
            <td><strong>Google SMTP</strong></td>
            <td>Sending notification emails</td>
            <td>Email address only</td>
          </tr>
          <tr>
            <td><strong>Cloudflare Insights</strong></td>
            <td>Basic usage analytics</td>
            <td>Aggregated only, no personal data</td>
          </tr>
          <tr>
            <td><strong>The Muse, Arbeitnow, Findwork, Jooble, Adzuna, Careerjet</strong></td>
            <td>Job listing data</td>
            <td>No user data shared with these providers</td>
          </tr>
        </tbody>
      </table>

      <hr />

      <h2>Our Goals for the Full Policy</h2>
      <p>When we publish a proper privacy policy it will:</p>
      <ul>
        <li>Accurately reflect exactly how the code works — verified against the actual codebase</li>
        <li>Cover GDPR, CCPA, COPPA, and FERPA properly</li>
        <li>Be reviewed by legal counsel before publication</li>
        <li>Be written in plain English, not legalese</li>
        <li>Be versioned and publicly diffable so you can see exactly what changed and when</li>
      </ul>
      <p>
        Until then, this page is our commitment. If you have questions about how UAH handles your
        data, email us at <a href="mailto:data@uahapp.com">data@uahapp.com</a> — we'll give you a
        straight answer.
      </p>

      <hr />

      <h2>Contact</h2>
      <p>
        <strong>Data &amp; privacy questions:</strong>
        <a href="mailto:data@uahapp.com">data@uahapp.com</a><br />
        <strong>General:</strong>
        <a href="mailto:admincontact@uahapp.com">admincontact@uahapp.com</a><br />
        <strong>Codebase:</strong>
        <a href="https://github.com/GUI2-G6/UAH" target="_blank" rel="noopener">
          github.com/GUI2-G6/UAH
        </a> — open source, go look for yourself
      </p>

      <hr />

      <p class="closing-note">
        <em>
          UAH is built by students who got tired of job searching being harder than it needs to be.
          We're not a company. We don't have investors. We're just trying to build something good
          and do it the right way.
        </em>
      </p>
      <p class="closing-note">
        <em>This page will be updated as UAH grows. The values on it won't change.</em>
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
.commitment-page {
  min-height: 100vh;
  padding: 48px 24px;
}

.commitment-container {
  max-width: 800px;
  margin: 0 auto;
  line-height: 1.7;
}

.page-header,
.page-footer {
  display: flex;
}

.page-header {
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.page-footer {
  margin-top: 32px;
}

h1 {
  font-size: 2rem;
  margin: 0;
}

h2 {
  font-size: 1.3rem;
  margin-top: 40px;
  margin-bottom: 12px;
}

hr {
  margin: 32px 0;
  border: none;
  border-top: 1px solid #e5e7eb;
}

p {
  margin-bottom: 16px;
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

ul {
  padding-left: 24px;
  margin-bottom: 16px;
}

ul li {
  margin-bottom: 8px;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 24px;
  font-size: 0.95rem;
}

th {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid #e5e7eb;
  font-weight: 600;
}

td {
  padding: 10px 12px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: top;
}

a {
  color: #2563eb;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

.subtitle {
  margin-bottom: 4px;
}

.last-updated {
  color: #6b7280;
  margin-bottom: 24px;
}

.closing-note {
  color: #6b7280;
}

@media (max-width: 640px) {
  .commitment-page {
    padding: 32px 16px;
  }
}
</style>
