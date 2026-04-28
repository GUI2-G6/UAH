<!-- Renders the sticky landing header and owns the mobile drawer state and lifecycle listeners. -->
<template>
  <header ref="headerRef" class="site-header">
    <div class="nav-shell">
      <div
        ref="navInnerRef"
        class="nav-inner"
        :class="{ 'is-compact-desktop': isCompactDesktop, 'is-drawer-mode': isDrawerMode }"
      >
        <RouterLink class="brand" to="/" @click="closeMenu">
          <img src="../images/logo.png" width="75" height="75" title="To Top" alt="Unified Application Hub home" />
          <span class="brand-copy">
            <strong id="title" title="Title">Unified Application Hub</strong>
            <span id="subtitle" title="Subtitle">Job applications made easy</span>
          </span>
        </RouterLink>

        <button
          ref="toggleRef"
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

        <nav
          ref="navPanelRef"
          class="nav-panel"
          id="site-nav-menu"
          aria-label="Primary"
          :aria-hidden="shouldHidePanel ? 'true' : 'false'"
          :inert="shouldHidePanel ? '' : null"
          :class="{ 'is-open': isMenuOpen }"
        >
          <div class="nav-links">
            <RouterLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              active-class="is-active"
              exact-active-class="is-active"
              @click="closeMenu"
            >
              {{ link.label }}
            </RouterLink>
          </div>
          <div class="nav-actions">
            <ThemeModeControl class="nav-theme-control" group-label="Site color theme" />
            <a class="nav-signin" :href="loginUrl" @click="closeMenu">Sign in</a>
          </div>
        </nav>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import ThemeModeControl from './ThemeModeControl.vue'

const isMenuOpen = ref(false)
const isMobileViewport = ref(false)
const isCompactDesktop = ref(false)
const isDesktopOverflowing = ref(false)
const loginUrl = (import.meta.env.VITE_UAH_LOGIN_URL || 'https://beta.uahapp.com/login').trim()
const mobileNavBreakpoint = 1080
const compactDesktopBreakpoint = 1320
const navInnerRef = ref(null)
const navPanelRef = ref(null)
const toggleRef = ref(null)
const headerRef = ref(null)
const lastFocusedElement = ref(null)
let resizeRunId = 0
let postMountRafId = 0
const route = useRoute()

const navLinks = [
  { to: '/', label: 'Home' },
  { to: '/status', label: 'Status' },
  { to: '/privacy-policy', label: 'Privacy Policy' },
  { to: '/terms', label: 'Terms' },
  { to: '/contributors', label: 'Contributors' },
  { to: '/ecosystem', label: 'Ecosystem' },
  { to: '/browser-extension', label: 'Extension (alpha)' },
  { to: '/provider-requests', label: 'Provider Requests' },
]

function closeMenu() {
  isMenuOpen.value = false
}

function navContentOverflowsDesktop() {
  const navInner = navInnerRef.value
  if (!(navInner instanceof HTMLElement)) {
    return false
  }
  if (navInner.scrollWidth > navInner.clientWidth + 1) {
    return true
  }

  // Some desktop layouts can visually collide before scrollWidth reports overflow.
  const brand = navInner.querySelector('.brand')
  const panel = navInner.querySelector('.nav-panel')
  if (!(brand instanceof HTMLElement) || !(panel instanceof HTMLElement)) {
    return false
  }

  const brandRect = brand.getBoundingClientRect()
  const panelRect = panel.getBoundingClientRect()
  if (brandRect.width <= 0 || panelRect.width <= 0) {
    return false
  }
  const collisionGap = 8

  return brandRect.right + collisionGap > panelRect.left
}

function updateHeaderHeightVar() {
  const header = headerRef.value
  if (!(header instanceof HTMLElement)) {
    return
  }
  const measured = Math.ceil(header.getBoundingClientRect().height)
  if (measured > 0) {
    document.documentElement.style.setProperty('--site-header-height', `${measured}px`)
  }
}

function setBackgroundInteractivity(blocked) {
  const targets = [document.querySelector('main'), document.querySelector('.site-footer')]
  targets.forEach((target) => {
    if (!(target instanceof HTMLElement)) return
    if (blocked) {
      target.setAttribute('aria-hidden', 'true')
      target.setAttribute('inert', '')
    } else {
      target.removeAttribute('aria-hidden')
      target.removeAttribute('inert')
    }
  })
}

function getFocusableNavItems() {
  const panel = navPanelRef.value
  if (!(panel instanceof HTMLElement)) return []
  return Array.from(
    panel.querySelectorAll(
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  ).filter((element) => element instanceof HTMLElement && element.offsetParent !== null)
}

async function focusFirstNavItem() {
  await nextTick()
  const [firstItem] = getFocusableNavItems()
  if (firstItem instanceof HTMLElement) {
    firstItem.focus()
  }
}

async function openMenu() {
  if (isMenuOpen.value) return
  lastFocusedElement.value = document.activeElement instanceof HTMLElement ? document.activeElement : null
  isMenuOpen.value = true
  updateHeaderHeightVar()
  await focusFirstNavItem()
}

function toggleMenu() {
  if (isMenuOpen.value) {
    closeMenu()
    return
  }
  void openMenu()
}

function handleKeydown(event) {
  if (event.key === 'Escape' && isMenuOpen.value) {
    event.preventDefault()
    closeMenu()
    return
  }
  if (event.key !== 'Tab' || !isMenuOpen.value || !isDrawerMode.value) {
    return
  }
  const focusables = getFocusableNavItems()
  if (!focusables.length) {
    return
  }
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const active = document.activeElement
  if (event.shiftKey && active === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && active === last) {
    event.preventDefault()
    first.focus()
  }
}

async function handleResize() {
  const width = window.innerWidth
  isMobileViewport.value = width <= mobileNavBreakpoint
  isCompactDesktop.value = width > mobileNavBreakpoint && width <= compactDesktopBreakpoint
  isDesktopOverflowing.value = false
  updateHeaderHeightVar()

  if (width > mobileNavBreakpoint) {
    closeMenu()
  }
}

const menuLabel = computed(() => (isMenuOpen.value ? 'Close navigation menu' : 'Open navigation menu'))
const isDrawerMode = computed(() => true)
const shouldHidePanel = computed(() => isDrawerMode.value && !isMenuOpen.value)

watch(isMenuOpen, (value) => {
  document.body.classList.toggle('nav-open', value)
  setBackgroundInteractivity(value && isDrawerMode.value)
  updateHeaderHeightVar()
  if (!value) {
    const previous = lastFocusedElement.value
    if (previous instanceof HTMLElement) {
      previous.focus()
    } else if (toggleRef.value instanceof HTMLElement) {
      toggleRef.value.focus()
    }
  }
})

if (route && typeof route === 'object' && 'fullPath' in route) {
  watch(
    () => route.fullPath,
    () => {
      closeMenu()
      void handleResize()
    }
  )
}

watch(isDrawerMode, (value) => {
  setBackgroundInteractivity(value && isMenuOpen.value)
})

onMounted(() => {
  void handleResize()
  postMountRafId = requestAnimationFrame(() => {
    void handleResize()
  })
  updateHeaderHeightVar()
  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', handleResize)
  window.addEventListener('uah-theme-changed', handleResize)
})

onUnmounted(() => {
  cancelAnimationFrame(postMountRafId)
  document.body.classList.remove('nav-open')
  document.documentElement.style.removeProperty('--site-header-height')
  setBackgroundInteractivity(false)
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('uah-theme-changed', handleResize)
})
</script>
