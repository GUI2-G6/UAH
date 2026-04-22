<!-- Renders the feedback form and preserves the existing mailto subject and body format exactly. -->
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
                    <label for="email">Email <span
                        style="font-weight:400;color:var(--color-muted);">(optional)</span></label>
                    <input id="email" v-model="form.email" name="email" type="email" autocomplete="email">
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
                  <button class="button" type="submit">Send Feedback</button>
                  <p class="small-note">Opens your email client with your responses pre-filled. We don't collect
                    anything from this page directly.</p>
                </div>
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
import { reactive } from 'vue'

const form = reactive({
  name: '',
  email: '',
  frustration: '',
  features: '',
  notify_public: false,
  interested_beta: false,
})

function valueOrFallback(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : 'Not provided'
}

function yesOrNo(value) {
  return value ? 'Yes' : 'No'
}

function handleSubmit() {
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
    'Interested in beta access: ' + yesOrNo(form.interested_beta)
  ]

  window.location.href = 'mailto:feedback@uahapp.com'
    + '?subject=' + encodeURIComponent('UAH Feature Request / Interest')
    + '&body=' + encodeURIComponent(lines.join('\r\n'))
}
</script>
