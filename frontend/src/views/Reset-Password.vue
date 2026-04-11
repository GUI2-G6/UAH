<template>
  <div class="page">
    <div class="auth-card">
      <h1>Reset password</h1>
      <p class="subtitle">Paste your reset token and choose a new password</p>

      <SecretInput
        v-model="token"
        id="reset-token"
        name="reset_token"
        inputClass="email-input"
        autocomplete="one-time-code"
        inputmode="text"
        autocapitalize="none"
        autocorrect="off"
        :spellcheck="false"
        placeholder="Reset token"
        :disabled="loading"
      />

      <SecretInput
        v-model="newPassword"
        id="reset-new-password"
        name="new_password"
        inputClass="email-input"
        autocomplete="new-password"
        inputmode="text"
        autocapitalize="none"
        autocorrect="off"
        :spellcheck="false"
        placeholder="New password"
        :disabled="loading"
      />

      <SecretInput
        v-model="confirmNewPassword"
        id="reset-confirm-password"
        name="confirm_new_password"
        inputClass="email-input"
        autocomplete="new-password"
        inputmode="text"
        autocapitalize="none"
        autocorrect="off"
        :spellcheck="false"
        placeholder="Confirm new password"
        :disabled="loading"
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
import SecretInput from '../components/SecretInput.vue'

export default {
  name: 'ResetPassword',
  components: {
    SecretInput,
  },
  data() {
    return {
      token: '',
      newPassword: '',
      confirmNewPassword: '',
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
        if (!this.newPassword || !this.confirmNewPassword) {
          throw new Error('Please enter and confirm your new password')
        }
        if (this.newPassword !== this.confirmNewPassword) {
          throw new Error('Passwords do not match')
        }

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
