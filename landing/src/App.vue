<!-- Renders the full standalone landing page and owns app-wide anchor-scroll enhancement. -->
<template>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <SiteHeader />

  <main id="main-content" tabindex="-1">
    <HeroSection />
    <ProblemSection />
    <WhatUAHDoes />
    <HowItsBuilt />
    <OpenSourceValues />
    <PartnersSection />
    <BetaAccess />
    <WishlistForm />
  </main>

  <SiteFooter />
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import SiteHeader from './components/SiteHeader.vue'
import HeroSection from './components/HeroSection.vue'
import ProblemSection from './components/ProblemSection.vue'
import WhatUAHDoes from './components/WhatUAHDoes.vue'
import HowItsBuilt from './components/HowItsBuilt.vue'
import OpenSourceValues from './components/OpenSourceValues.vue'
import PartnersSection from './components/PartnersSection.vue'
import BetaAccess from './components/BetaAccess.vue'
import WishlistForm from './components/WishlistForm.vue'
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
