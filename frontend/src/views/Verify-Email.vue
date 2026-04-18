<template>
  <div class="page">
    <div class="auth-card">
      <h1>Email verification</h1>
      <p v-if="loading" class="subtitle">Verifying your email securely...</p>
      <p v-else-if="error" class="subtitle">{{ error }}</p>
      <p v-else class="subtitle">Email verified. Redirecting to Settings...</p>
      <button v-if="error" class="submit-btn" @click="goToSettings">Open Settings</button>
    </div>
  </div>
</template>

<script>
import { readApiError } from '../lib/auth.js'

function toReasonCode(error) {
  const message = String(error || '').toLowerCase()
  if (!message) return 'verification_failed'
  if (message.includes('expired')) return 'expired'
  if (message.includes('invalid')) return 'invalid_token'
  if (message.includes('not found')) return 'user_not_found'
  return 'verification_failed'
}

export default {
  name: 'Verify-Email',
  data() {
    return {
      loading: true,
      error: '',
    }
  },
  async mounted() {
    await this.verifyFromLink()
  },
  methods: {
    async verifyFromLink() {
      const token = typeof this.$route?.query?.token === 'string' ? this.$route.query.token.trim() : ''
      if (!token) {
        this.loading = false
        this.error = 'Verification link is missing a token.'
        return
      }

      try {
        const res = await fetch('/api/account/verify-email', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        })

        if (!res.ok) {
          const message = await readApiError(res)
          throw new Error(message || `HTTP ${res.status}`)
        }

        this.loading = false
        this.$router.replace({
          path: '/settings',
          query: { verify_email: 'success' },
        })
      } catch (e) {
        this.loading = false
        this.error = e?.message ?? 'Verification failed.'
        this.$router.replace({
          path: '/settings',
          query: {
            verify_email: 'error',
            verify_reason: toReasonCode(e?.message),
          },
        })
      }
    },
    goToSettings() {
      this.$router.push('/settings')
    },
  },
}
</script>

<style scoped src="./css/Login.css"></style>
