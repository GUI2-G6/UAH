<template>
    <footer class="footer">
        <p>&copy; 2026 UAH. All rights reserved.</p>
        <p class="footer-credit">Icons credited to Nicholas Johnson.</p>
    <nav>
        <router-link to="/status">Status</router-link>
        <button v-if="showDebugTools" type="button" class="footer-link-button footer-link-button-dev" @click="$emit('open-debug-view')">Debug Tools · Dev only</button>
        <router-link to="/our-commitment">Our Commitment</router-link>
        <p>Contact us: <a href="mailto:support@uahapp.com">support@uahapp.com</a></p>
        </nav>
    </footer>
</template>

<script>
    export default{
        name: "Footer",
        props: {
            showDebugTools: {
                type: Boolean,
                default: false,
            },
        },
        emits: ["open-debug-view"]
    }
</script>

<style src="./css/Footer.css"></style>
