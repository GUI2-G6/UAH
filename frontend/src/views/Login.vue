<template>
    <div class="page">
        <div class="auth-card">
            <h1>Login</h1>
            <p class="subtitle">Track every application in one place</p>

            <form @submit.prevent="login" novalidate>
                <input
                    id="login-email"
                    name="email"
                    class="email-input"
                    type="email"
                    v-model="email"
                    autocomplete="username"
                    autocapitalize="none"
                    autocorrect="off"
                    spellcheck="false"
                    placeholder="Email"
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

            <p v-if="message" class="auth-feedback auth-feedback--success">{{ message }}</p>
            <p v-if="error" class="auth-feedback auth-feedback--error">{{ error }}</p>

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
    import { readApiError, setAuth } from "../lib/auth.js";
    import { assertValidEmail } from "../lib/validation.js";

    export default{
        name: "Login",
        components: {
            SecretInput
        },
        data() {
            return {
                email: "",
                password: "",
                loading: false,
                oauthRedirecting: false,
                message: null,
                error: null,
            }
        },
        mounted() {
            if (this.$route?.query?.registered === '1') {
                this.message = 'Account created! Please check your email to verify your address before logging in.'
            }
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
                this.message = null
                this.error = null
                try {
                    const email = assertValidEmail(this.email)
                    const res = await fetch('/api/auth/login', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            email,
                            password: this.password,
                        }),
                    })

                    if (!res.ok) {
                        const message = await readApiError(res)
                        const error = new Error(message || `HTTP ${res.status}`)
                        error.status = res.status
                        throw error
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
