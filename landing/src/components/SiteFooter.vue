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
        <ThemeModeControl compact group-label="Color theme" />
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/status">Status</RouterLink>
        <RouterLink to="/our-commitment">Privacy Policy</RouterLink>
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
import { RouterLink } from 'vue-router'
import ThemeModeControl from './ThemeModeControl.vue'
</script>
