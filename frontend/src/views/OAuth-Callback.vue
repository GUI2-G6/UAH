<template>
  <div class="page">
    <div class="auth-card">
      <h1>Finishing sign in</h1>
      <p v-if="loading" class="subtitle">Completing your Google sign-in session...</p>
      <p v-else-if="error" class="subtitle">{{ error }}</p>
      <p v-else class="subtitle">Signed in successfully. Redirecting...</p>
      <button v-if="error" class="submit-btn" @click="goToLogin">Back to login</button>
    </div>
  </div>
</template>

<script>
import { clearAuth, setAuth, syncCurrentUser } from '../lib/auth.js'

function parseOAuthParams(route) {
  const hash = String(window.location.hash || '').replace(/^#/, '')
  const hashParams = new URLSearchParams(hash)
  const queryParams = new URLSearchParams(window.location.search || '')

  return {
    accessToken: hashParams.get('access_token') || queryParams.get('access_token') || '',
    next: hashParams.get('next') || route?.query?.next || '/home',
    provider: hashParams.get('provider') || queryParams.get('provider') || 'google',
    oauthError: queryParams.get('oauth') || '',
    reason: queryParams.get('reason') || '',
  }
}

function sanitizeNextPath(nextPath) {
  const value = String(nextPath || '').trim()
  if (!value || !value.startsWith('/') || value.startsWith('//')) return '/home'
  return value
}

export default {
  name: 'OAuth-Callback',
  data() {
    return {
      loading: true,
      error: '',
    }
  },
  async mounted() {
    await this.completeOAuth()
  },
  methods: {
    async completeOAuth() {
      const payload = parseOAuthParams(this.$route)
      if (payload.oauthError === 'error') {
        this.loading = false
        this.error = `Google sign-in failed${payload.reason ? ` (${payload.reason.replace(/_/g, ' ')})` : ''}.`
        return
      }

      try {
        if (payload.accessToken) {
          setAuth({ access_token: payload.accessToken })
        }
        const user = await syncCurrentUser({ force: true })
        if (!user) throw new Error('No authenticated session')
        this.$router.replace(sanitizeNextPath(payload.next))
      } catch (e) {
        clearAuth()
        this.loading = false
        this.error = `Could not complete ${payload.provider} sign-in. Please try again.`
      }
    },
    goToLogin() {
      this.$router.push('/login')
    },
  },
}
</script>

<style scoped src="./css/Login.css"></style>
