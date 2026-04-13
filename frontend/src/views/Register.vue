<template>
  <div class="page">
    <div class="auth-card">
      <h1>Create account</h1>
      <p class="subtitle">Create an account to access UAH</p>
      <form @submit.prevent="register">
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

      <div class="oauth-divider" aria-hidden="true">
        <span>or</span>
      </div>

      <button
        type="button"
        class="oauth-btn"
        :disabled="loading || oauthRedirecting"
        @click="startGoogleOAuth"
      >
        {{ oauthRedirecting ? 'Redirecting to Google…' : 'Continue with Google' }}
      </button>

      <p v-if="error" class="subtitle">{{ error }}</p>

      <div class="signup-row">
        <span>Already have an account?</span>
        <a @click.prevent="goToLogin" href="#">Sign in</a>
      </div>
    </div>
  </div>
</template>

<script>
import SecretInput from '../components/SecretInput.vue'
import { setAuth } from '../lib/auth.js'
import { assertValidEmail } from '../lib/validation.js'

export default {
  name: 'Register',
  components: {
    SecretInput,
  },
  data() {
    return {
      email: '',
      confirmEmail: '',
      password: '',
      confirmPassword: '',
      first_name: '',
      last_name: '',
      loading: false,
      oauthRedirecting: false,
      error: null,
    }
  },
  mounted() {
    const oauthError = this.$route?.query?.oauth
    const reason = this.$route?.query?.reason
    if (oauthError === 'error') {
      this.error = `Google sign-in failed${reason ? ` (${String(reason).replaceAll('_', ' ')})` : ''}`
    }
  },
  methods: {
    storeAuth(data) {
      setAuth(data)
    },
    async register() {
      this.loading = true
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
            email,
            password: this.password,
            first_name: this.first_name || null,
            last_name: this.last_name || null,
          }),
        })

        if (!res.ok) {
          const text = await res.text()
          throw new Error(text || `HTTP ${res.status}`)
        }

        const data = await res.json()
        this.storeAuth(data)
        const next = this.$route?.query?.next
        this.$router.push(typeof next === 'string' && next.length ? next : '/home')
      } catch (e) {
        this.error = e?.message ?? String(e)
      } finally {
        this.loading = false
      }
    },
    goToLogin() {
      this.$router.push('/login')
    },
    startGoogleOAuth() {
      this.error = null
      this.oauthRedirecting = true
      const next = typeof this.$route?.query?.next === 'string' ? this.$route.query.next : ''
      const params = new URLSearchParams({ intent: 'register' })
      if (next) params.set('next', next)
      window.location.assign(`/api/auth/google?${params.toString()}`)
    },
  },
}
</script>

<style scoped src="./css/Login.css"></style>
