<template>
  <div class="page">
    <div class="auth-card">
      <button
        type="button"
        class="landing-btn landing-btn--back"
        :disabled="loading || oauthRedirecting"
        @click="goToLanding"
      >
        Back to access options
      </button>
      <h1>Create your beta account</h1>
      <p class="subtitle">
        This invite-only beta registration flow is for approved users only. You need a valid beta invite code
        to create your account and start using UAH.
      </p>
      <p class="auth-note auth-note--soft">
        Need approval first?
        <a href="#" @click.prevent="showBetaRequestForm = true">Request beta access</a>
      </p>
      <form @submit.prevent="register">
        <label class="auth-label" for="register-invite-code">Invite Code</label>
        <input
          id="register-invite-code"
          name="invite_code"
          class="email-input"
          :class="{ 'field-input-error': !!inviteCodeError }"
          type="text"
          v-model="inviteCode"
          required
          :disabled="loading"
          :aria-invalid="inviteCodeError ? 'true' : 'false'"
          aria-describedby="register-invite-code-error"
          autocomplete="one-time-code"
          autocapitalize="none"
          autocorrect="off"
          spellcheck="false"
          placeholder="Invite Code"
          @input="inviteCodeError = null"
        />
        <p v-if="inviteCodeError" id="register-invite-code-error" class="field-error">{{ inviteCodeError }}</p>
        <input id="register-email" name="email" class="email-input" type="email" v-model="email" autocomplete="email" autocapitalize="none" autocorrect="off" spellcheck="false" placeholder="Email" />
        <input id="register-confirm-email" name="confirm_email" class="email-input" type="email" v-model="confirmEmail" autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false" placeholder="Confirm email" />
        <SecretInput v-model="password" id="register-password" name="new-password" inputClass="email-input" autocomplete="new-password" inputmode="text" autocapitalize="none" autocorrect="off" :spellcheck="false" placeholder="Password" :disabled="loading" />
        <SecretInput v-model="confirmPassword" id="register-confirm-password" name="confirm_password" inputClass="email-input" autocomplete="new-password" inputmode="text" autocapitalize="none" autocorrect="off" :spellcheck="false" placeholder="Confirm password" :disabled="loading" />
        <input id="register-first-name" name="first_name" class="email-input" type="text" v-model="first_name" autocomplete="given-name" placeholder="First name" />
        <input id="register-last-name" name="last_name" class="email-input" type="text" v-model="last_name" autocomplete="family-name" placeholder="Last name" />
        <button class="submit-btn" type="submit" :disabled="loading">
          {{ loading ? 'Creating…' : 'Create account' }}
        </button>
      </form>
      <div class="auth-note">
        <strong>Google sign-in comes later.</strong>
        After you create your account and sign in normally, you can optionally link Google later from
        Settings under <strong>Sign-in Methods</strong>.
      </div>

      <p v-if="message" class="auth-feedback auth-feedback--success">{{ message }}</p>
      <p v-if="error" class="auth-feedback auth-feedback--error">{{ error }}</p>
      <div v-if="showBetaRequestForm" class="auth-note auth-note--soft beta-request-panel">
        <strong>Beta access request</strong>
        <p>Share the email we should review for invite approval.</p>
        <form class="beta-request-form" @submit.prevent="submitBetaRequest">
          <input
            id="register-beta-request-email"
            class="email-input"
            type="email"
            v-model.trim="betaRequestEmail"
            autocomplete="email"
            placeholder="you@example.com"
            :disabled="betaRequestSubmitting"
            required
          />
          <button class="submit-btn" type="submit" :disabled="betaRequestSubmitting || !betaRequestEmail">
            {{ betaRequestSubmitting ? 'Submitting…' : 'Submit beta request' }}
          </button>
        </form>
        <p v-if="betaRequestMessage" class="auth-feedback auth-feedback--success">{{ betaRequestMessage }}</p>
        <p v-if="betaRequestError" class="auth-feedback auth-feedback--error">{{ betaRequestError }}</p>
      </div>

      <div class="signup-row">
        <span>Already have an account?</span>
        <a @click.prevent="goToLogin" href="#">Sign in</a>
      </div>
      <div class="signup-row">
        <a href="#" @click.prevent="showBetaRequestForm = true">Request beta access</a>
      </div>
    </div>
  </div>
</template>

<script>
import SecretInput from '../components/SecretInput.vue'
import { logout, readApiError } from '../lib/auth.js'
import { assertValidEmail } from '../lib/validation.js'

export default {
  name: 'Register',
  components: {
    SecretInput,
  },
  data() {
    return {
      inviteCode: '',
      email: '',
      confirmEmail: '',
      password: '',
      confirmPassword: '',
      first_name: '',
      last_name: '',
      loading: false,
      oauthRedirecting: false,
      inviteCodeError: null,
      message: null,
      error: null,
      showBetaRequestForm: false,
      betaRequestEmail: '',
      betaRequestSubmitting: false,
      betaRequestMessage: '',
      betaRequestError: '',
    }
  },
  mounted() {
    const oauthError = this.$route?.query?.oauth
    const reason = this.$route?.query?.reason
    if (oauthError === 'error') {
      this.error = this.googleOAuthErrorMessage(reason)
    }
  },
  methods: {
    googleOAuthErrorMessage(reason) {
      if (reason === 'google_not_linked') {
        return 'Google sign-in is only available after you create an account and link Google later from Settings.'
      }
      return `Google sign-in failed${reason ? ` (${String(reason).replaceAll('_', ' ')})` : ''}`
    },
    async register() {
      this.loading = true
      this.inviteCodeError = null
      this.message = null
      this.error = null
      try {
        const email = assertValidEmail(this.email)
        const confirmEmail = assertValidEmail(this.confirmEmail, 'confirm email')
        if (!email || !confirmEmail || email.toLowerCase() !== confirmEmail.toLowerCase()) {
          throw new Error('Emails do not match')
        }
        if (!this.password || !this.confirmPassword || this.password !== this.confirmPassword) {
          throw new Error('Passwords do not match')
        }

        const res = await fetch('/api/auth/register', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            invite_code: String(this.inviteCode || '').trim(),
            email,
            password: this.password,
            first_name: this.first_name || null,
            last_name: this.last_name || null,
          }),
        })

        if (!res.ok) {
          const message = await readApiError(res)
          const error = new Error(message || `HTTP ${res.status}`)
          error.status = res.status
          throw error
        }

        await res.json()
        await logout()
        this.message = 'Account created! Please check your email to verify your address before logging in.'
        window.setTimeout(() => {
          this.$router.push({
            path: '/login',
            query: { registered: '1' },
          })
        }, 1200)
      } catch (e) {
        const message = e?.message ?? String(e)
        if (e?.status === 400 && message === 'Invalid or expired invite code') {
          this.inviteCodeError = message
          return
        }
        this.error = message
      } finally {
        this.loading = false
      }
    },
    goToLogin() {
      this.$router.push('/login')
    },
    goToLanding() {
      this.$router.push('/landing')
    },
    async submitBetaRequest() {
      this.betaRequestSubmitting = true
      this.betaRequestMessage = null
      this.betaRequestError = null
      try {
        const res = await fetch('/api/public/beta-access', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: this.betaRequestEmail,
            source_surface: 'frontend_register',
          }),
        })
        const payload = await res.json().catch(() => ({}))
        if (!res.ok) {
          throw new Error(payload?.detail || payload?.message || `Request failed (HTTP ${res.status})`)
        }
        this.betaRequestMessage = payload?.message || 'Thanks - your beta access request has been received.'
        this.betaRequestEmail = ''
      } catch (error) {
        this.betaRequestError = error?.message || 'Unable to submit beta request right now.'
      } finally {
        this.betaRequestSubmitting = false
      }
    },
  },
}
</script>

<style scoped src="./css/Login.css"></style>
