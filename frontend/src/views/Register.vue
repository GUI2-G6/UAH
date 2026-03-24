<template>
  <div class="page">
    <div class="auth-card">
      <h1>Create account</h1>
      <p class="subtitle">Create an account to access UAH</p>

      <input class="email-input" type="email" v-model="email" autocomplete="email" placeholder="Email" />
      <input class="email-input" type="text" v-model="username" autocomplete="username" placeholder="Username" />
      <input class="email-input" type="password" v-model="password" autocomplete="new-password" placeholder="Password" />
      <input class="email-input" type="text" v-model="first_name" autocomplete="given-name" placeholder="First name" />
      <input class="email-input" type="text" v-model="last_name" autocomplete="family-name" placeholder="Last name" />

      <button class="submit-btn" @click="register" :disabled="loading">
        {{ loading ? 'Creating…' : 'Create account' }}
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
export default {
  name: 'Register',
  data() {
    return {
      email: '',
      username: '',
      password: '',
      first_name: '',
      last_name: '',
      loading: false,
      error: null,
    }
  },
  methods: {
    storeAuth(data) {
      if (data?.access_token) {
        localStorage.setItem('uah_access_token', data.access_token)
      }
      if (data?.user) {
        localStorage.setItem('uah_current_user', JSON.stringify(data.user))
      }
    },
    async register() {
      this.loading = true
      this.error = null
      try {
        const res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: this.email,
            username: this.username,
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
  },
}
</script>

<style scoped src="./css/Login.css"></style>
