<!-- Renders the full standalone landing page and owns app-wide anchor-scroll enhancement. -->
<template>
  <div class="app-shell">
    <a class="skip-link" href="#main-content">Skip to content</a>
    <SiteHeader />

    <router-view />

    <SiteFooter />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import SiteHeader from './components/SiteHeader.vue'
import SiteFooter from './components/SiteFooter.vue'

const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')

function handleAnchorClick(event) {
  const link = event.target instanceof Element ? event.target.closest('a[href^="#"]') : null
  if (!link) {
    return
  }

  const hash = link.getAttribute('href')
  if (!hash || !hash.startsWith('#')) {
    return
  }

  const target = document.querySelector(hash)
  if (!target) {
    return
  }

  event.preventDefault()
  target.focus({ preventScroll: true })
  target.scrollIntoView({
    behavior: motionQuery.matches ? 'auto' : 'smooth',
    block: 'start'
  })

  if (window.history && window.history.pushState) {
    window.history.pushState(null, '', hash)
  } else {
    window.location.hash = hash
  }
}

onMounted(() => {
  document.documentElement.classList.add('js-enabled')
  document.addEventListener('click', handleAnchorClick)
})

onUnmounted(() => {
  document.documentElement.classList.remove('js-enabled')
  document.body.classList.remove('nav-open')
  document.removeEventListener('click', handleAnchorClick)
})
</script>

<style>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-shell > main {
  flex: 1;
}
</style>
