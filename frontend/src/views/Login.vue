<template>
    <div class="page">
        <div class="auth-card">
            <h1>Login</h1>
            <p class="subtitle">Track every application in one place</p>

            <form @submit.prevent="login">
                <input
                    id="login-username"
                    name="username"
                    class="email-input"
                    type="text"
                    v-model="username"
                    autocomplete="username"
                    autocapitalize="none"
                    autocorrect="off"
                    spellcheck="false"
                    placeholder="Username"
                />
                <SecretInput
                    v-model="password"
                    id="login-password"
                    name="current-password"
                    inputClass="email-input"
                    autocomplete="current-password"
                    inputmode="text"
                    autocapitalize="none"
                    autocorrect="off"
                    :spellcheck="false"
                    placeholder="Password"
                    :disabled="loading"
                />

                <button type="submit" class="submit-btn" :disabled="loading">
                    {{ loading ? 'Signing in…' : 'Sign in' }}
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
                <span>Don't have an account?</span>
                <a @click.prevent="goToRegister" href="#">Create an account</a>
            </div>

            <div class="signup-row">
                <a @click.prevent="goToForgotPassword" href="#">Forgot password?</a>
            </div>
        </div>
    </div>
</template>


<script>
    import SecretInput from "../components/SecretInput.vue";
    import { setAuth } from "../lib/auth.js";

    export default{
        name: "Login",
        components: {
            SecretInput,
        },
        data() {
            return {
                username: "",
                password: "",
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
            goToRegister() {
                this.$router.push('/register')
            },
            goToForgotPassword() {
                this.$router.push('/forgot-password')
            },
            startGoogleOAuth() {
                this.error = null
                this.oauthRedirecting = true
                const next = typeof this.$route?.query?.next === 'string' ? this.$route.query.next : ''
                const params = new URLSearchParams({ intent: 'login' })
                if (next) params.set('next', next)
                window.location.assign(`/api/auth/google?${params.toString()}`)
            },
        },
    }
</script>

<style scoped src="./css/Login.css"></style>
