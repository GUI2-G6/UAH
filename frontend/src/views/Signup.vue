<template>
    <div class="page">
        <div class="auth-card">
            <h1>Signup</h1>
            <p class="subtitle">Redirecting to account creation…</p>
            <button class="submit-btn" @click="goToRegister">Go to Create Account</button>
        </div>
        </div>
</template>


<script>
    export default{
        name: "Signup",
        mounted() {
            this.$router.replace('/register')
        },
        methods: {
            goToRegister() {
                this.$router.push('/register')
            },
        },
    }
</script>

<style src="./css/Login.css"></style>