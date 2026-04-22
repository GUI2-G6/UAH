<template>
  <main id="main-content" tabindex="-1">
    <HeroSection />
    <ProblemSection />
    <WhatUAHDoes />
    <HowItsBuilt />
    <OpenSourceValues />
    <PartnersSection />
    <BetaAccess />
    <WishlistForm />

    <section class="section-shell" aria-labelledby="transparency-links-heading">
      <div class="section-card">
        <p class="section-label">Public Pages</p>
        <h2 id="transparency-links-heading">Explore the full transparency hub.</h2>
        <p class="section-intro">
          UAH now separates status, commitment, contributors, ecosystem context, and provider requests into
          dedicated public pages so each topic stays clear and easy to share.
        </p>
        <div class="page-link-grid">
          <RouterLink class="page-link-card" to="/status">
            <strong>Status</strong>
            <p>Live public-safe service summary, refreshed from `/api/status`.</p>
          </RouterLink>
          <RouterLink class="page-link-card" to="/our-commitment">
            <strong>Our Commitment</strong>
            <p>Data handling principles, beta transparency, and contact paths.</p>
          </RouterLink>
          <RouterLink class="page-link-card" to="/contributors">
            <strong>Contributors</strong>
            <p>Permanent credit model and current core contributors.</p>
          </RouterLink>
          <RouterLink class="page-link-card" to="/ecosystem">
            <strong>Ecosystem</strong>
            <p>Official partners, integrated providers, and framework guardrails.</p>
          </RouterLink>
          <RouterLink class="page-link-card" to="/provider-requests">
            <strong>Provider Requests</strong>
            <p>Partnership interest and provider removal workflows with proof requirements.</p>
          </RouterLink>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'

import BetaAccess from '../components/BetaAccess.vue'
import HeroSection from '../components/HeroSection.vue'
import HowItsBuilt from '../components/HowItsBuilt.vue'
import OpenSourceValues from '../components/OpenSourceValues.vue'
import PartnersSection from '../components/PartnersSection.vue'
import ProblemSection from '../components/ProblemSection.vue'
import WhatUAHDoes from '../components/WhatUAHDoes.vue'
import WishlistForm from '../components/WishlistForm.vue'
</script>
