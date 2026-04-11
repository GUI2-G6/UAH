<template>
    <footer class="footer">
        <p>&copy; 2026 UAH. All rights reserved.</p>
    <nav>
        <router-link to="/status">Status</router-link>
        <button v-if="showDebugTools" type="button" class="footer-link-button footer-link-button-dev" @click="$emit('open-debug-view')">Debug Tools · Dev only</button>
        <p>Privacy Policy(PlaceholderForNow)</p> <!--This is a placeholder for the privacy policy link. It should be updated with the actual URL when available.-->
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
