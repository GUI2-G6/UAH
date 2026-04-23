<template>
  <section id="wishlist" tabindex="-1">
    <div class="section-shell">
      <div class="section-card">
        <p class="section-label">Community input</p>
        <h2>Help us build what you actually need.</h2>
        <p class="quote">
          "We will read every response. Features that come up more than once move up the backlog. Nothing you suggest
          is automatically off the table — we'd rather hear the ambitious version of what you want and figure out how
          to build it."
        </p>

        <div class="wishlist-grid">
          <div>
            <p class="section-intro" style="margin-bottom:20px;">
              We're not looking for engagement metrics or feature validation theater. We want grounded, honest
              feedback from people who are actually doing the job search and know firsthand what makes it painful.
            </p>
            <ul class="signal-list" aria-label="How your feedback is used">
              <li>Repeated pain points get prioritized.</li>
              <li>Feature requests tell us what to build next.</li>
              <li>Beta interest tells us who gets invited first.</li>
            </ul>
          </div>

          <div class="form-card">
            <form id="wishlist-form" @submit.prevent="handleSubmit">
              <div class="form-grid">
                <div class="form-row">
                  <div class="field">
                    <label for="name">Name <span
                        style="font-weight:400;color:var(--color-muted);">(optional)</span></label>
                    <input id="name" v-model="form.name" name="name" type="text" autocomplete="name">
                  </div>
                  <div class="field">
                    <label for="email">Email <span style="font-weight:700;color:var(--color-text);">(required)</span></label>
                    <input
                      id="email"
                      v-model.trim="form.email"
                      name="email"
                      type="email"
                      autocomplete="email"
                      required
                      :disabled="submitting"
                    >
                  </div>
                </div>
                <div class="field">
                  <label for="frustration">What frustrates you most about your current job search?</label>
                  <textarea id="frustration" v-model="form.frustration" name="frustration"
                    placeholder="Be as specific as you want. The more detail, the more useful."></textarea>
                </div>
                <div class="field">
                  <label for="features">What would you want in a job search and tracking tool?</label>
                  <textarea id="features" v-model="form.features" name="features"
                    placeholder="Anything from basic improvements to things that don't exist yet."></textarea>
                </div>
                <div class="checklist">
                  <label class="checkbox" for="notify-public">
                    <input id="notify-public" v-model="form.notify_public" name="notify_public" type="checkbox"
                      value="yes">
                    <span>Notify me when UAH opens public access.</span>
                  </label>
                  <label class="checkbox" for="interested-beta">
                    <input id="interested-beta" v-model="form.interested_beta" name="interested_beta" type="checkbox"
                      value="yes">
                    <span>I'd also like to be considered for beta access.</span>
                  </label>
                </div>
                <div class="form-actions">
                  <button
                    class="button"
                    type="submit"
                    :disabled="submitting || !form.email"
                    :aria-busy="submitting"
                  >
                    {{ submitting ? 'Sending…' : 'Send feedback' }}
                  </button>
                  <p class="small-note">
                    Your answers are sent securely to our team when you submit. You do not need to open your email app
                    for us to receive them.
                  </p>
                  <p class="small-note">
                    <button type="button" class="link-button" :disabled="submitting" @click="openMailtoFallback">
                      Open in my email app instead
                    </button>
                    <span class="muted-inline"> (optional; same content as below)</span>
                  </p>
                </div>
                <p
                  v-if="feedback"
                  id="wishlist-feedback"
                  class="wishlist-feedback"
                  :class="feedbackClass"
                  role="status"
                  aria-live="polite"
                >
                  {{ feedback }}
                </p>
                <p class="small-note">We read every message. Your email is never sold or shared.</p>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { messageFromApiFailure } from '../lib/apiErrorMessage.js'

const form = reactive({
  name: '',
  email: '',
  frustration: '',
  features: '',
  notify_public: false,
  interested_beta: false,
})

const feedback = ref('')
const feedbackKind = ref('idle')
const submitting = ref(false)
const lastAttemptAt = ref(0)
const MIN_MS_BETWEEN_ATTEMPTS = 5000

const feedbackClass = computed(() => ({
  'wishlist-feedback--success': feedbackKind.value === 'success',
  'wishlist-feedback--warn': feedbackKind.value === 'warn',
  'wishlist-feedback--error': feedbackKind.value === 'error',
}))

function setFeedback(kind, text) {
  feedbackKind.value = kind
  feedback.value = text
}

function valueOrFallback(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : 'Not provided'
}

function yesOrNo(value) {
  return value ? 'Yes' : 'No'
}

function buildMailtoHref() {
  const lines = [
    'UAH Feature Request / Interest',
    '',
    'Name: ' + valueOrFallback(form.name),
    'Email: ' + valueOrFallback(form.email),
    '',
    'What frustrates you most about your current job search?',
    valueOrFallback(form.frustration),
    '',
    'What would you want in a job search and tracking tool?',
    valueOrFallback(form.features),
    '',
    'Notify when public access opens: ' + yesOrNo(form.notify_public),
    'Interested in beta access: ' + yesOrNo(form.interested_beta),
  ]
  return (
    'mailto:feedback@uahapp.com' +
    '?subject=' +
    encodeURIComponent('UAH Feature Request / Interest') +
    '&body=' +
    encodeURIComponent(lines.join('\r\n'))
  )
}

function openMailtoFallback() {
  try {
    window.location.href = buildMailtoHref()
    setFeedback(
      'success',
      'We asked your system to open your email app with this feedback pre-filled. You can still use “Send feedback” above so we receive it without email. If nothing opened, copy feedback@uahapp.com and paste your text manually.'
    )
  } catch {
    setFeedback(
      'warn',
      'Your browser could not start the email handoff. Use “Send feedback” above, or email feedback@uahapp.com and paste the same details.'
    )
  }
}

async function handleSubmit() {
  const now = Date.now()
  if (now - lastAttemptAt.value < MIN_MS_BETWEEN_ATTEMPTS) {
    setFeedback(
      'warn',
      'Please wait a few seconds before sending again. This limits repeated requests from scripts or double-clicks.'
    )
    return
  }
  lastAttemptAt.value = now
  setFeedback('idle', '')
  submitting.value = true

  try {
    const response = await fetch('/api/public/landing-feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: form.email,
        full_name: form.name.trim() || null,
        frustration: form.frustration.trim() || null,
        features: form.features.trim() || null,
        notify_public: Boolean(form.notify_public),
        interested_beta: Boolean(form.interested_beta),
        source_surface: 'landing_wishlist',
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
    setFeedback('success', payload?.message || 'Thanks — we received your feedback.')
    form.name = ''
    form.email = ''
    form.frustration = ''
    form.features = ''
    form.notify_public = false
    form.interested_beta = false
  } catch (error) {
    setFeedback('error', error instanceof Error ? error.message : 'Could not reach the server. Check your connection and try again.')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.wishlist-feedback {
  margin: 0.35rem 0 0;
  font-size: 0.92rem;
  line-height: 1.45;
}

.wishlist-feedback--success {
  color: #137333;
}

.wishlist-feedback--warn {
  color: #7a4e00;
}

.wishlist-feedback--error {
  color: #8b1c1c;
}

.link-button {
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  font: inherit;
  color: var(--color-primary, #1a5fb4);
  text-decoration: underline;
  cursor: pointer;
}

.link-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.muted-inline {
  color: var(--color-muted, #666);
  font-size: 0.9em;
}
</style>
