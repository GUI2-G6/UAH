<!-- Renders the landing footer and preserves the simple link set and attribution line. -->
<template>
  <footer class="site-footer">
    <div class="footer-shell">
      <div class="footer-brand">
        <div>
          <strong>UAH</strong>
          <span>Unified Application Hub</span>
        </div>
        <p class="footer-note">Built by Group 6 at UMass Lowell &middot; Open Source &middot; Free Forever</p>
      </div>
      <div class="footer-links" aria-label="Footer links">
        <button
          type="button"
          class="footer-theme-toggle"
          :aria-label="'Theme: ' + themeLabel + '. Click to cycle system, light, and dark.'"
          @click="cycleTheme"
        >
          Theme: {{ themeLabel }}
        </button>
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/status">Status</RouterLink>
        <RouterLink to="/our-commitment">Our Commitment</RouterLink>
        <RouterLink to="/contributors">Contributors</RouterLink>
        <RouterLink to="/ecosystem">Ecosystem</RouterLink>
        <RouterLink to="/provider-requests">Provider Requests</RouterLink>
        <a href="https://github.com/GUI2-G6/UAH" target="_blank" rel="noopener noreferrer">GitHub</a>
        <a href="mailto:team@uahapp.com">Contact</a>
        <a href="mailto:press@uahapp.com">Press</a>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  getStoredPreference,
  setPreferenceAndApply,
  nextThemePreference,
  themePreferenceLabel,
} from '@shared/js/themePreference.js'

const themeLabel = ref('System')

function syncLabel() {
  themeLabel.value = themePreferenceLabel(getStoredPreference() ?? 'system')
}

function cycleTheme() {
  const cur = getStoredPreference() ?? 'system'
  setPreferenceAndApply(nextThemePreference(cur))
  syncLabel()
}

function onThemeChanged() {
  syncLabel()
}

onMounted(() => {
  syncLabel()
  window.addEventListener('uah-theme-changed', onThemeChanged)
  window.addEventListener('storage', onThemeChanged)
})

onUnmounted(() => {
  window.removeEventListener('uah-theme-changed', onThemeChanged)
  window.removeEventListener('storage', onThemeChanged)
})
</script>

<style scoped>
.footer-theme-toggle {
  border: none;
  background: none;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  font-size: 0.94rem;
  color: var(--color-primary);
  padding: 0;
  text-decoration: none;
}

.footer-theme-toggle:hover,
.footer-theme-toggle:focus-visible {
  text-decoration: underline;
}
</style>
