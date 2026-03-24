<template>
  <div class="page">
    <div class="auth-card">
      <h1>Forgot password</h1>
      <p class="subtitle">Enter your email to receive a reset token</p>

      <input
        class="email-input"
        type="email"
        v-model="email"
        autocomplete="email"
        placeholder="Email"
      />

      <button
        class="submit-btn"
        :class="{ 'is-success': !!message && !loading, 'is-error': !!error && !loading }"
        @click="submit"
        :disabled="loading"
      >
        {{ loading ? 'Sending…' : 'Send reset token' }}
      </button>

      <p v-if="message" class="subtitle">{{ message }}</p>
      <p v-if="error" class="subtitle">{{ error }}</p>

      <div class="signup-row">
        <a @click.prevent="goToReset" href="#">I already have a token</a>
        <span>·</span>
        <a @click.prevent="goToLogin" href="#">Back to login</a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ForgotPassword',
  data() {
    return {
      email: '',
      loading: false,
      error: null,
      message: null,
    }
  },
  methods: {
    async submit() {
      this.loading = true
      this.error = null
      this.message = null
      try {
        const res = await fetch('/api/account/forgot-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: this.email }),
        })

        const data = await res.json().catch(() => null)
        if (!res.ok) {
          throw new Error(data?.detail || `HTTP ${res.status}`)
        }

        this.message = data?.message || 'If that email exists, a reset link has been sent'
      } catch (e) {
        this.error = e?.message ?? String(e)
      } finally {
        this.loading = false
      }
    },
    goToLogin() {
      this.$router.push('/login')
    },
    goToReset() {
      this.$router.push('/reset-password')
    },
  },
}
</script>

<style scoped src="./css/Login.css"></style>
