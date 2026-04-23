import { createRouter, createWebHistory } from 'vue-router'

import BrowserExtensionPage from '../pages/BrowserExtensionPage.vue'
import ContributorsPage from '../pages/ContributorsPage.vue'
import EcosystemPage from '../pages/EcosystemPage.vue'
import HomePage from '../pages/HomePage.vue'
import OurCommitmentPage from '../pages/OurCommitmentPage.vue'
import ProviderRequestsPage from '../pages/ProviderRequestsPage.vue'
import PublicStatusPage from '../pages/PublicStatusPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage,
    },
    {
      path: '/status',
      name: 'status',
      component: PublicStatusPage,
    },
    {
      path: '/our-commitment',
      name: 'our-commitment',
      component: OurCommitmentPage,
    },
    {
      path: '/contributors',
      name: 'contributors',
      component: ContributorsPage,
    },
    {
      path: '/ecosystem',
      name: 'ecosystem',
      component: EcosystemPage,
    },
    {
      path: '/provider-requests',
      name: 'provider-requests',
      component: ProviderRequestsPage,
    },
    {
      path: '/browser-extension',
      name: 'browser-extension',
      component: BrowserExtensionPage,
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    if (to.hash) {
      return { el: to.hash, top: 88 }
    }
    return { top: 0 }
  },
})

router.afterEach(() => {
  requestAnimationFrame(() => {
    const mainContent = document.querySelector('#main-content')
    if (mainContent instanceof HTMLElement) {
      mainContent.focus({ preventScroll: true })
    }
  })
})

export default router
