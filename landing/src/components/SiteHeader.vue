<!-- Renders the sticky landing header and owns the mobile drawer state and lifecycle listeners. -->
<template>
  <header class="site-header">
    <div class="nav-shell">
      <div class="nav-inner">
        <a class="brand" href="#top" @click="closeMenu">
          <img src="../images/logo.png" width="75" height="75" title="To Top"/>
          <span class="brand-copy">
            <strong id="title" title="Title">Unified Application Hub</strong>
            <span id="subtitle" title="Subtitle">Job applications made easy</span>
          </span>
        </a>

        <button
          class="nav-toggle"
          type="button"
          :aria-expanded="String(isMenuOpen)"
          aria-controls="site-nav-menu"
          :aria-label="menuLabel"
          @click="toggleMenu"
        >
          <span class="nav-toggle-line" aria-hidden="true"></span>
        </button>

        <div class="nav-overlay" data-nav-overlay :class="{ 'is-open': isMenuOpen }" @click="closeMenu"></div>

        <nav class="nav-panel" id="site-nav-menu" aria-label="Primary" :class="{ 'is-open': isMenuOpen }">
          <div class="nav-links">
            <a v-for="link in navLinks" :key="link.href" :href="link.href" @click="closeMenu">{{ link.label }}</a>
          </div>
          <div class="nav-actions">
            <a class="nav-signin" :href="loginUrl" @click="closeMenu">Sign in</a>
          </div>
        </nav>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const isMenuOpen = ref(false)
const loginUrl = (import.meta.env.VITE_UAH_LOGIN_URL || 'https://beta.uahapp.com/login').trim()
const mobileNavBreakpoint = 1080

const navLinks = [
  { href: '#problem', label: 'The Problem' },
  { href: '#what-uah-does', label: 'What UAH Does' },
  { href: '#built', label: "How It's Built" },
  { href: '#values', label: 'Open Source' },
  { href: '#partners', label: 'Partners' },
  { href: '#access', label: 'Beta Access' },
  { href: '#wishlist', label: 'Wishlist' },
]

function closeMenu() {
  isMenuOpen.value = false
}

function toggleMenu() {
  isMenuOpen.value = !isMenuOpen.value
}

function handleKeydown(event) {
  if (event.key === 'Escape') {
    closeMenu()
  }
}

function handleResize() {
  if (window.innerWidth > mobileNavBreakpoint) {
    closeMenu()
  }
}

const menuLabel = computed(() => (isMenuOpen.value ? 'Close navigation menu' : 'Open navigation menu'))

watch(isMenuOpen, (value) => {
  document.body.classList.toggle('nav-open', value)
})

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  document.body.classList.remove('nav-open')
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', handleResize)
})
</script>
