<template>
    <footer class="footer">
        <p class="footer-copy">&copy; 2026 UAH. All rights reserved.</p>
        <p class="footer-credit">Icons credited to Nicholas Johnson.</p>
        <nav class="footer-nav" aria-label="Public pages">
            <button
                type="button"
                class="footer-link-button footer-theme-toggle"
                :aria-label="'Theme: ' + footerThemeLabel + '. Click to cycle system, light, and dark.'"
                @click="cycleFooterTheme"
            >
                Theme: {{ footerThemeLabel }}
            </button>
            <button type="button" class="footer-link-button" data-test="footer-link-home" @click="openPublicPage('/', 'Landing home')">Landing</button>
            <button type="button" class="footer-link-button" data-test="footer-link-status" @click="openPublicPage('/status', 'Status')">Status</button>
            <button type="button" class="footer-link-button" data-test="footer-link-commitment" @click="openPublicPage('/our-commitment', 'Our Commitment')">Our Commitment</button>
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
    import {
        getStoredPreference,
        setPreferenceAndApply,
        nextThemePreference,
        themePreferenceLabel,
    } from '@shared/js/themePreference.js'

    const DEFAULT_PUBLIC_LANDING_URL = 'https://uahapp.com'

    export default{
        name: "Footer",
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
                footerThemeLabel: 'System',
            }
        },
        created() {
            const configuredBase = String(import.meta.env.VITE_PUBLIC_LANDING_URL || '').trim()
            this.publicLandingBaseUrl = configuredBase || DEFAULT_PUBLIC_LANDING_URL
        },
        mounted() {
            this.syncFooterThemeLabel()
            this._footerThemeHandler = () => this.syncFooterThemeLabel()
            window.addEventListener('uah-theme-changed', this._footerThemeHandler)
            window.addEventListener('storage', this._footerThemeHandler)
        },
        beforeUnmount() {
            if (this._footerThemeHandler) {
                window.removeEventListener('uah-theme-changed', this._footerThemeHandler)
                window.removeEventListener('storage', this._footerThemeHandler)
            }
        },
        methods: {
            syncFooterThemeLabel() {
                this.footerThemeLabel = themePreferenceLabel(getStoredPreference() ?? 'system')
            },
            cycleFooterTheme() {
                const cur = getStoredPreference() ?? 'system'
                setPreferenceAndApply(nextThemePreference(cur))
                this.syncFooterThemeLabel()
            },
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
