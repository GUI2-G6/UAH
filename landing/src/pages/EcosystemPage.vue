<template>
  <main id="main-content" tabindex="-1">
    <section class="section-shell page-shell" aria-labelledby="ecosystem-heading">
      <div class="section-card page-card">
        <p class="section-label">Ecosystem</p>
        <h1 id="ecosystem-heading" class="page-title">Clear ecosystem terminology and transparency</h1>
        <p class="section-intro">
          To reduce confusion, UAH separates official partnerships from integrations under published terms and from
          our responsible collection framework. These categories are not interchangeable.
        </p>

        <div class="policy-grid">
          <article class="policy-card">
            <h2>Official Partners</h2>
            <p>
              Organizations with direct correspondence and explicit acknowledgment of our usage/integration path.
            </p>
            <ul class="detail-list">
              <li>WhatJobs (official partner)</li>
              <li>Additional official partners will be listed as confirmed.</li>
            </ul>
            <p>
              Interested in becoming an official partner?
              <RouterLink to="/provider-requests">Start here</RouterLink>.
            </p>
          </article>

          <article class="policy-card">
            <h2>Integrated Data Providers</h2>
            <p>
              APIs and data sources currently used under their published free/public usage terms, without implying
              formal partnership.
            </p>
            <ul class="detail-list">
              <li>The Muse</li>
              <li>Arbeitnow</li>
              <li>Findwork</li>
              <li>Jooble</li>
              <li>Adzuna</li>
              <li>Careerjet</li>
            </ul>
          </article>
        </div>

        <article class="policy-card policy-card-wide">
          <h2>Responsible Collection Framework</h2>
          <p>
            UAH maintains a modular framework with policy guardrails: robots/terms checks, request pacing controls,
            transparent provider documentation, and quick opt-out/removal handling.
          </p>
          <p>
            We do not treat provider resources as unlimited. The framework is designed to be respectful, auditable,
            and easy to halt when required.
          </p>
        </article>

        <article class="policy-card policy-card-wide">
          <h2>Provider removal and compliance</h2>
          <p>
            We honor legitimate provider removal requests. For provider-level changes we require proof of
            affiliation/ownership/authority before acting to prevent unauthorized disruptions.
          </p>
          <p>
            Submit requests through the
            <RouterLink to="/provider-requests">Provider Requests page</RouterLink>.
          </p>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>
