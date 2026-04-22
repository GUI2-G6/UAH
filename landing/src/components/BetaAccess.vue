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
              on that process — not a polished product, but the process of building something worth using — send a
              request below.
            </p>
            <div class="access-links">
              <form class="access-form" @submit.prevent="submitRequest">
                <label class="access-label" for="beta-request-email">Request beta access</label>
                <div class="access-form-row">
                  <input
                    id="beta-request-email"
                    v-model.trim="email"
                    class="access-input"
                    type="email"
                    autocomplete="email"
                    required
                    :disabled="submitting"
                    placeholder="you@example.com"
                  />
                  <button class="button" type="submit" :disabled="submitting || !email">
                    {{ submitting ? 'Sending...' : 'Submit request' }}
                  </button>
                </div>
                <p v-if="feedback" class="access-feedback" :class="{ 'access-feedback-error': feedbackIsError }">{{ feedback }}</p>
              </form>
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
              <li>You can submit a request here or use the wishlist form below for additional context.</li>
            </ul>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

const email = ref('')
const feedback = ref('')
const feedbackIsError = ref(false)
const submitting = ref(false)

async function submitRequest() {
  feedback.value = ''
  feedbackIsError.value = false
  submitting.value = true

  try {
    const response = await fetch('/api/public/beta-access', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.value,
        source_surface: 'landing_beta_access',
      }),
    })

    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      const errorMessage = payload?.detail || payload?.message || `Request failed (HTTP ${response.status}).`
      throw new Error(errorMessage)
    }

    feedback.value = payload?.message || 'Thanks - your beta access request has been received.'
    email.value = ''
  } catch (error) {
    feedbackIsError.value = true
    feedback.value = error instanceof Error ? error.message : 'Unable to submit request right now.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.access-form {
  display: grid;
  gap: 8px;
  width: min(100%, 420px);
}

.access-label {
  font-weight: 700;
  color: var(--color-text);
}

.access-form-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.access-input {
  flex: 1 1 220px;
  min-height: 42px;
  border: 1px solid rgba(31, 92, 153, 0.28);
  border-radius: 12px;
  padding: 0 12px;
  font: inherit;
}

.access-feedback {
  margin: 0;
  color: #137333;
  font-size: 0.92rem;
}

.access-feedback-error {
  color: #b3261e;
}
</style>
