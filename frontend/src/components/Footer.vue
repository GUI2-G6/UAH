<template>
    <footer class="footer">
        <p>&copy; 2026 UAH. All rights reserved.</p>
    <nav>
        <router-link to="/status">Status</router-link>
        <button type="button" class="footer-link-button" @click="$emit('open-debug-view')">Debug Diagnostic View</button>
        <p>Privacy Policy(PlaceholderForNow)</p> <!--This is a placeholder for the privacy policy link. It should be updated with the actual URL when available.-->
        <p>Contact us: <a href="mailto:support@uahapp.com">support@uahapp.com</a></p>
        </nav>
    </footer>
</template>

<script>
    export default{
        name: "Footer",
        emits: ["open-debug-view"]
    }
</script>

<style src="./css/Footer.css"></style>