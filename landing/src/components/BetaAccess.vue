<!-- Renders the closed-beta access section with explicit framing around rough edges, feedback, and Cloudflare gating. -->
<template>
  <section id="access" tabindex="-1">
    <div class="section-shell">
      <div class="section-card">
        <p class="section-label">Beta access</p>
        <h2>Get early access.</h2>
        <div class="access-grid">
          <article class="access-card primary">
            <strong>The beta is live. Access is invite-only for now.</strong>
            <p class="callout-text">
              UAH beta is live at <a href="https://beta.uahapp.com" target="_blank" rel="noopener noreferrer"
                style="color:var(--color-primary);font-weight:700;">beta.uahapp.com</a>. Real people are using it. It
              also has rough edges, missing features, and things we know need work. We are being deliberate about who we
              onboard because every tester's experience and feedback directly shapes what we build next. If you want in
              on that process — not a polished product, but the process of building something worth using — reach out.
            </p>
            <div class="access-links">
              <a class="button" href="mailto:admincontact@uahapp.com?subject=UAH Beta Access Request">Request access
                by email</a>
              <a class="button-secondary" href="https://beta.uahapp.com" target="_blank"
                rel="noopener noreferrer">Visit beta.uahapp.com</a>
            </div>
            <p class="support-note">If you are not approved yet, the beta URL will return a Cloudflare auth screen.
              That's expected. The site is gated, not broken.</p>
          </article>
          <article class="access-card">
            <strong>What to include in your request</strong>
            <ul class="access-steps">
              <li>Your name.</li>
              <li>What kind of job search you're doing — student, entry level, career change, or something else.</li>
              <li>Which features you're most interested in testing or helping shape first.</li>
              <li>You can request access by email or use the wishlist form below. Both paths work.</li>
            </ul>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>
