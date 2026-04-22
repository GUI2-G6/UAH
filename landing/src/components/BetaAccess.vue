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
              <form class="access-form" @submit.prevent="submitRequest" novalidate>
                <label class="access-label" for="beta-request-email">Request beta access</label>
                <div class="access-form-row">
                  <input
                    id="beta-request-email"
                    v-model.trim="email"
                    class="access-input"
                    type="email"
                    autocomplete="email"
                    inputmode="email"
                    required
                    :disabled="submitting"
                    :aria-invalid="feedbackKind === 'error' ? 'true' : 'false'"
                    :aria-describedby="feedback ? 'beta-access-feedback' : undefined"
                    placeholder="you@example.com"
                  />
                  <button
                    class="button"
                    type="submit"
                    :disabled="submitting || !email"
                    :aria-busy="submitting"
                  >
                    {{ submitting ? 'Sending...' : 'Submit request' }}
                  </button>
                </div>
                <p
                  v-if="feedback"
                  id="beta-access-feedback"
                  class="access-feedback"
                  :class="feedbackClass"
                  role="status"
                  aria-live="polite"
                >
                  {{ feedback }}
                </p>
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
import { computed, ref } from 'vue'
import { messageFromApiFailure } from '../lib/apiErrorMessage.js'

const email = ref('')
const feedback = ref('')
const feedbackKind = ref('idle')
const submitting = ref(false)
const lastAttemptAt = ref(0)

const MIN_MS_BETWEEN_ATTEMPTS = 3500

const feedbackClass = computed(() => ({
  'access-feedback--success': feedbackKind.value === 'success',
  'access-feedback--warn': feedbackKind.value === 'warn',
  'access-feedback--error': feedbackKind.value === 'error',
}))

function setFeedback(kind, text) {
  feedbackKind.value = kind
  feedback.value = text
}

async function submitRequest() {
  const now = Date.now()
  if (now - lastAttemptAt.value < MIN_MS_BETWEEN_ATTEMPTS) {
    setFeedback(
      'warn',
      'Please wait a few seconds between attempts. This slows down accidental double-clicks and automated abuse.'
    )
    return
  }
  lastAttemptAt.value = now

  setFeedback('idle', '')
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
      if (response.status === 429) {
        setFeedback('warn', messageFromApiFailure(response, payload))
      } else {
        setFeedback('error', messageFromApiFailure(response, payload))
      }
      return
    }

    setFeedback('success', payload?.message || 'Thanks — we received your request. If you are selected for beta, we will follow up at the email you provided.')
    email.value = ''
  } catch (error) {
    setFeedback('error', error instanceof Error ? error.message : 'Could not reach the server. Check your connection and try again.')
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
  font-size: 0.92rem;
  line-height: 1.45;
}

.access-feedback--success {
  color: #137333;
}

.access-feedback--warn {
  color: #7a4e00;
}

.access-feedback--error {
  color: #b3261e;
}
</style>
