<template>
    <div class="page">
        <div class="auth-card">
            <h1>Create account</h1>
            <p class="subtitle">
                This legacy signup link now points to the same invite-only beta account creation flow as the
                main access chooser.
            </p>
            <button class="submit-btn" @click="goToRegister">Create account</button>
            <button class="landing-btn" @click="goToLanding">Back to access options</button>
        </div>
    </div>
</template>


<script>
    export default{
        name: "Signup",
        methods: {
            goToRegister() {
                this.$router.push('/register')
            },
            goToLanding() {
                this.$router.push('/landing')
            },
        },
    }
</script>

<style src="./css/Login.css"></style>