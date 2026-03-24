<template>
  <div class="page">
    <div class="auth-card">
      <h1>Reset password</h1>
      <p class="subtitle">Paste your reset token and choose a new password</p>

      <input
        class="email-input"
        type="text"
        v-model="token"
        autocomplete="off"
        placeholder="Reset token"
      />

      <input
        class="email-input"
        type="password"
        v-model="newPassword"
        autocomplete="new-password"
        placeholder="New password"
      />

      <button
        class="submit-btn"
        :class="{ 'is-success': !!message && !loading, 'is-error': !!error && !loading }"
        @click="submit"
        :disabled="loading"
      >
        {{ loading ? 'Resetting…' : 'Reset password' }}
      </button>

      <p v-if="message" class="subtitle">{{ message }}</p>
      <p v-if="error" class="subtitle">{{ error }}</p>

      <div class="signup-row">
        <a @click.prevent="goToForgot" href="#">Need a token?</a>
        <span>·</span>
        <a @click.prevent="goToLogin" href="#">Back to login</a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResetPassword',
  data() {
    return {
      token: '',
      newPassword: '',
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
        const res = await fetch('/api/account/reset-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            token: this.token,
            new_password: this.newPassword,
          }),
        })

        const data = await res.json().catch(() => null)
        if (!res.ok) {
          throw new Error(data?.detail || `HTTP ${res.status}`)
        }

        this.message = data?.message || 'Password reset successfully'
        // Send user back to login after a short beat.
        setTimeout(() => {
          this.$router.push('/login')
        }, 250)
      } catch (e) {
        this.error = e?.message ?? String(e)
      } finally {
        this.loading = false
      }
    },
    goToLogin() {
      this.$router.push('/login')
    },
    goToForgot() {
      this.$router.push('/forgot-password')
    },
  },
}
</script>

<style scoped src="./css/Login.css"></style>
