<template>
    <footer class="footer">
        <p class="footer-copy">&copy; 2026 UAH. All rights reserved.</p>
        <p class="footer-credit">Icons credited to Nicholas Johnson.</p>
        <nav class="footer-nav" aria-label="Public pages">
            <ThemeModeControl class="footer-theme-control" compact group-label="Color theme" />
            <button type="button" class="footer-link-button" data-test="footer-link-home" @click="openPublicPage('/', 'Landing home')">Landing</button>
            <button type="button" class="footer-link-button" data-test="footer-link-status" @click="openPublicPage('/status', 'Status')">Status</button>
            <button type="button" class="footer-link-button" data-test="footer-link-privacy" @click="openPublicPage('/privacy-policy', 'Privacy Policy')">Privacy Policy</button>
            <button type="button" class="footer-link-button" data-test="footer-link-terms" @click="openPublicPage('/terms', 'Terms of Service')">Terms</button>
            <button type="button" class="footer-link-button" data-test="footer-link-contributors" @click="openPublicPage('/contributors', 'Contributors')">Contributors</button>
            <button type="button" class="footer-link-button" data-test="footer-link-ecosystem" @click="openPublicPage('/ecosystem', 'Ecosystem')">Ecosystem</button>
            <button type="button" class="footer-link-button" data-test="footer-link-provider-requests" @click="openPublicPage('/provider-requests', 'Provider Requests')">Provider Requests</button>
            <button v-if="showDebugTools" type="button" class="footer-link-button footer-link-button-dev" @click="$emit('open-debug-view')">Debug Tools · Dev only</button>
        </nav>
        <p class="footer-contact">Contact us: <a href="mailto:support@uahapp.com">support@uahapp.com</a></p>
    </footer>
</template>

<script>
    import { showToast } from '@/services/toastService.js'
    import ThemeModeControl from './ThemeModeControl.vue'

    const DEFAULT_PUBLIC_LANDING_URL = 'https://uahapp.com'

    export default{
        name: "Footer",
        components: {
            ThemeModeControl,
        },
        props: {
            showDebugTools: {
                type: Boolean,
                default: false,
            },
        },
        emits: ["open-debug-view"],
        data() {
            return {
                publicLandingBaseUrl: DEFAULT_PUBLIC_LANDING_URL,
            }
        },
        created() {
            const configuredBase = String(import.meta.env.VITE_PUBLIC_LANDING_URL || '').trim()
            this.publicLandingBaseUrl = configuredBase || DEFAULT_PUBLIC_LANDING_URL
        },
        methods: {
            normalizedLandingBase() {
                return this.publicLandingBaseUrl.replace(/\/+$/, '')
            },
            openPublicPage(path, label) {
                const normalizedPath = path.startsWith('/') ? path : `/${path}`
                const destination = `${this.normalizedLandingBase()}${normalizedPath}`
                const openedWindow = window.open(destination, '_blank', 'noopener,noreferrer')

                if (!openedWindow) {
                    showToast('Popup blocked. Opening destination in this tab instead.', 'error')
                    window.location.assign(destination)
                    return
                }

                showToast(`${label} opened in a new tab.`, 'success')
            },
        },
    }
</script>

<style src="./css/Footer.css"></style>
