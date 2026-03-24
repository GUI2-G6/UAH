<template>
    <div class="page">
        <div class="auth-card">
            <h1>Login</h1>
            <p class="subtitle">Track every application in one place</p>

            <input
                class="email-input"
                type="text"
                v-model="username"
                autocomplete="username"
                placeholder="Username"
            />
            <input
                class="email-input"
                type="password"
                v-model="password"
                autocomplete="current-password"
                placeholder="Password"
            />

            <button class="submit-btn" @click="login" :disabled="loading">
                {{ loading ? 'Signing in…' : 'Sign in' }}
            </button>

            <p v-if="error" class="subtitle">{{ error }}</p>

            <div class="signup-row">
                <span>Don't have an account?</span>
                <a @click.prevent="goToRegister" href="#">Create an account</a>
            </div>

            <div class="signup-row">
                <a @click.prevent="goToForgotPassword" href="#">Forgot password?</a>
            </div>

            <div class="bypass-section">
                <span class="bypass-title">Alpha override</span>
                <input
                    class="email-input"
                    type="password"
                    v-model="bypassPassphrase"
                    autocomplete="off"
                    placeholder="Admin bypass passphrase"
                />
                <button class="submit-btn" @click="bypass" :disabled="loading">
                    {{ loading ? 'Checking…' : 'Bypass login' }}
                </button>
            </div>
        </div>
    </div>
</template>


<script>
    export default{
        name: "Login",
        data() {
            return {
                username: "",
                password: "",
                bypassPassphrase: "",
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
            async login() {
                this.loading = true
                this.error = null
                try {
                    const res = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            username: this.username,
                            password: this.password,
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
            async bypass() {
                this.loading = true
                this.error = null
                try {
                    const host = window.location.hostname
                    const isLocalDev = host === 'localhost' || host === '127.0.0.1' || host === '::1'

                    if (isLocalDev) {
                        this.storeAuth({
                            access_token: 'local-dev-bypass',
                            user: {
                                id: 0,
                                email: 'local@dev',
                                username: 'local-dev',
                                first_name: 'Local',
                                last_name: 'Dev',
                                avatar_url: null,
                                email_verified: false,
                                is_active: true,
                            },
                        })
                        const next = this.$route?.query?.next
                        this.$router.push(typeof next === 'string' && next.length ? next : '/home')
                        return
                    }

                    const res = await fetch('/api/auth/bypass', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            passphrase: this.bypassPassphrase,
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
                    // If backend is down locally, allow bypass anyway.
                    const host = window.location.hostname
                    const isLocalDev = host === 'localhost' || host === '127.0.0.1' || host === '::1'
                    if (isLocalDev) {
                        this.storeAuth({
                            access_token: 'local-dev-bypass',
                            user: {
                                id: 0,
                                email: 'local@dev',
                                username: 'local-dev',
                                first_name: 'Local',
                                last_name: 'Dev',
                                avatar_url: null,
                                email_verified: false,
                                is_active: true,
                            },
                        })
                        const next = this.$route?.query?.next
                        this.$router.push(typeof next === 'string' && next.length ? next : '/home')
                        return
                    }

                    this.error = e?.message ?? String(e)
                } finally {
                    this.loading = false
                }
            },
            goToRegister() {
                this.$router.push('/register')
            },
            goToForgotPassword() {
                this.$router.push('/forgot-password')
            },
        },
    }
</script>

<style scoped src="./css/Login.css"></style>