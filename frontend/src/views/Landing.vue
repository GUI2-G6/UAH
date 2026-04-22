<template>
  <section class="landing-gateway">
    <div class="landing-card">
      <p class="eyebrow">Unified Application Hub</p>
      <h1>Beta access is invite-only.</h1>
      <p class="subtitle">
        Use the path that matches where you are right now: sign in if you already have an account, create
        one if you were invited, or request beta access first if you still need approval.
      </p>

      <div class="path-grid">
        <article class="path-card path-card-primary">
          <p class="path-label">Returning users</p>
          <h2>Already have an account?</h2>
          <p class="path-copy">
            Sign in to the UAH beta with your email and password. If you already linked Google in Settings,
            you can use Google from the sign-in page too.
          </p>
          <div class="actions">
            <router-link class="button primary" to="/login">Sign in</router-link>
          </div>
        </article>

        <article class="path-card path-card-invite">
          <p class="path-label">Invited beta users</p>
          <h2>Have an invite code?</h2>
          <p class="path-copy">
            Create your account here if your beta access was approved and you already have the invite code
            you need for registration.
          </p>
          <div class="actions">
            <router-link class="button secondary" to="/register">Create account</router-link>
            <button class="button tertiary" type="button" @click="showBetaRequestForm = true">Request beta access</button>
          </div>
        </article>
      </div>

      <article class="path-card path-card-support">
        <p class="path-label">Still deciding?</p>
        <div class="support-grid">
          <div class="support-copy">
            <h2>Need the full overview first?</h2>
            <p class="path-copy">
              Read the public landing page for product details, current beta status, the wishlist form, and
              the best route for requesting access.
            </p>
          </div>
          <div class="actions actions-vertical">
            <a class="button tertiary" :href="marketingUrl" target="_blank" rel="noopener noreferrer">
              Open the public landing page
            </a>
            <button class="button tertiary" type="button" @click="showBetaRequestForm = true">Request beta access</button>
          </div>
        </div>
      </article>

      <article v-if="showBetaRequestForm" class="path-card path-card-request">
        <p class="path-label">Access request</p>
        <h2>Submit a beta request</h2>
        <p class="path-copy">
          Share the email we should contact for invite review. We will follow up if your request is selected.
        </p>
        <form class="request-form" @submit.prevent="submitBetaRequest">
          <input
            v-model.trim="betaRequestEmail"
            class="request-input"
            type="email"
            autocomplete="email"
            required
            :disabled="betaRequestSubmitting"
            placeholder="you@example.com"
          />
          <button class="button secondary" type="submit" :disabled="betaRequestSubmitting || !betaRequestEmail">
            {{ betaRequestSubmitting ? 'Submitting…' : 'Submit request' }}
          </button>
        </form>
        <p v-if="betaRequestMessage" class="request-feedback request-feedback--success">{{ betaRequestMessage }}</p>
        <p v-if="betaRequestError" class="request-feedback request-feedback--error">{{ betaRequestError }}</p>
      </article>

      <p class="meta">
        Opening the app without an active session sends you here first so returning users, invited beta
        users, and new visitors each get a clear next step.
      </p>
    </div>
  </section>
</template>

<script>
const DEFAULT_MARKETING_URL = 'https://uahapp.com'

export default {
  name: 'Landing',
  data() {
    return {
      marketingUrl: DEFAULT_MARKETING_URL,
      showBetaRequestForm: false,
      betaRequestEmail: '',
      betaRequestSubmitting: false,
      betaRequestMessage: '',
      betaRequestError: '',
    }
  },
  created() {
    const configured = String(import.meta.env.VITE_PUBLIC_LANDING_URL || '').trim()
    this.marketingUrl = configured || DEFAULT_MARKETING_URL
  },
  methods: {
    async submitBetaRequest() {
      this.betaRequestSubmitting = true
      this.betaRequestMessage = ''
      this.betaRequestError = ''
      try {
        const res = await fetch('/api/public/beta-access', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: this.betaRequestEmail,
            source_surface: 'frontend_landing',
          }),
        })
        const payload = await res.json().catch(() => ({}))
        if (!res.ok) {
          throw new Error(payload?.detail || payload?.message || `Request failed (HTTP ${res.status})`)
        }
        this.betaRequestMessage = payload?.message || 'Thanks - your beta access request has been received.'
        this.betaRequestEmail = ''
      } catch (error) {
        this.betaRequestError = error instanceof Error ? error.message : 'Unable to submit beta request.'
      } finally {
        this.betaRequestSubmitting = false
      }
    },
  },
}
</script>

<style scoped>
.landing-gateway {
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.landing-card {
  width: min(860px, 100%);
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  box-shadow: 0 24px 40px rgba(15, 23, 42, 0.08);
  padding: 2.5rem;
}

.eyebrow {
  margin: 0 0 0.8rem;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f6f8f;
}

h1 {
  margin: 0;
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  line-height: 1.15;
  color: #0f172a;
}

.subtitle {
  margin: 1rem 0 0;
  max-width: 64ch;
  color: #334155;
  line-height: 1.6;
}

.path-grid {
  margin-top: 1.8rem;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.path-card {
  display: grid;
  gap: 0.95rem;
  padding: 1.35rem;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.82);
}

.path-card-primary {
  background: linear-gradient(180deg, rgba(15, 111, 143, 0.08) 0%, rgba(248, 250, 252, 0.92) 100%);
}

.path-card-invite {
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.04) 0%, rgba(248, 250, 252, 0.94) 100%);
}

.path-card-support {
  margin-top: 1rem;
}

.path-card-request {
  margin-top: 1rem;
}

.path-label {
  margin: 0;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f6f8f;
}

h2 {
  margin: 0;
  font-size: 1.3rem;
  line-height: 1.2;
  color: #0f172a;
}

.path-copy {
  margin: 0;
  color: #334155;
  line-height: 1.6;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
}

.actions-vertical {
  flex-direction: column;
  align-items: stretch;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 150px;
  padding: 0.72rem 1.1rem;
  border-radius: 999px;
  font-weight: 700;
  text-decoration: none;
  border: none;
  cursor: pointer;
}

.button.primary {
  background: #0f172a;
  color: #f8fafc;
}

.button.secondary {
  border: 1px solid #0f172a;
  color: #0f172a;
}

.button.tertiary {
  border: 1px solid rgba(15, 111, 143, 0.25);
  color: #0f6f8f;
  background: #ffffff;
}

.support-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(220px, 0.8fr);
  gap: 1rem;
  align-items: start;
}

.request-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.request-input {
  flex: 1 1 280px;
  min-height: 44px;
  border: 1px solid rgba(15, 23, 42, 0.2);
  border-radius: 12px;
  padding: 0.65rem 0.8rem;
  font: inherit;
}

.request-feedback {
  margin: 0;
  font-size: 0.94rem;
}

.request-feedback--success {
  color: #166534;
}

.request-feedback--error {
  color: #b91c1c;
}

.meta {
  margin-top: 1.2rem;
  color: #475569;
  line-height: 1.6;
}

@media (max-width: 640px) {
  .landing-card {
    padding: 1.5rem;
    border-radius: 16px;
  }

  .path-grid {
    grid-template-columns: 1fr;
  }

  .support-grid {
    grid-template-columns: 1fr;
  }

  .button {
    width: 100%;
  }

  .actions {
    flex-direction: column;
  }
}
</style>
