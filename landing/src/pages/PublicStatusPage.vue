<template>
  <main id="main-content" tabindex="-1">
    <section class="section-shell page-shell" aria-labelledby="public-status-heading">
      <div class="section-card page-card">
        <p class="section-label">Status</p>
        <h1 id="public-status-heading" class="page-title">Public status overview</h1>
        <p class="section-intro">
          This page shares a public-safe operational summary. Internal diagnostics stay access-controlled and
          include deeper engineering details that are not exposed here.
        </p>

        <div v-if="loading" class="status-banner status-banner-neutral">
          <strong>Checking live status...</strong>
          <p>Refreshing data from `/api/status`.</p>
        </div>

        <div v-else-if="error" class="status-banner status-banner-danger">
          <strong>Status temporarily unavailable</strong>
          <p>{{ error }}</p>
        </div>

        <div v-else class="status-banner" :class="bannerClass">
          <strong>{{ overallTitle }}</strong>
          <p>{{ statusPayload.message }}</p>
        </div>

        <p class="status-meta" v-if="statusPayload.timestamp">
          Last updated: {{ formatTimestamp(statusPayload.timestamp) }}
        </p>

        <div class="status-grid">
          <article class="status-card" v-for="summary in serviceSummaries" :key="summary.service">
            <div class="status-card-head">
              <h2>{{ formatServiceName(summary.service) }}</h2>
              <span class="status-chip" :class="statusClass(summary.status)">
                {{ summary.status }}
              </span>
            </div>
            <p>{{ summary.summary }}</p>
          </article>
        </div>

        <div class="status-actions">
          <button class="button-secondary" type="button" @click="loadStatus" :disabled="loading">
            {{ loading ? 'Refreshing...' : 'Refresh status' }}
          </button>
          <RouterLink class="button-secondary" to="/provider-requests">Report provider concern</RouterLink>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

const loading = ref(true)
const error = ref('')
const statusPayload = ref({
  status: 'degraded',
  overall: 'degraded',
  message: 'Status unavailable',
  timestamp: '',
  service_summaries: [],
})

const serviceSummaries = computed(() => {
  const summaries = statusPayload.value?.service_summaries
  if (Array.isArray(summaries) && summaries.length > 0) {
    return summaries
  }
  const services = statusPayload.value?.services || {}
  return Object.entries(services).map(([service, info]) => ({
    service,
    status: info?.status || 'degraded',
    summary: info?.summary || 'No summary available yet.',
  }))
})

const bannerClass = computed(() => {
  const overall = statusPayload.value?.overall
  if (overall === 'healthy') return 'status-banner-good'
  if (overall === 'unhealthy') return 'status-banner-danger'
  return 'status-banner-warn'
})

const overallTitle = computed(() => {
  const overall = statusPayload.value?.overall
  if (overall === 'healthy') return 'All core public checks are healthy'
  if (overall === 'unhealthy') return 'Some services are currently disrupted'
  return 'Some services are running in a degraded state'
})

function statusClass(status) {
  if (status === 'healthy') return 'status-chip-good'
  if (status === 'unhealthy') return 'status-chip-danger'
  return 'status-chip-warn'
}

function formatServiceName(name) {
  return String(name || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatTimestamp(value) {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return 'Unknown'
  }
  return parsed.toLocaleString()
}

async function loadStatus() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/status')
    if (!response.ok) {
      throw new Error(`Status endpoint returned HTTP ${response.status}.`)
    }
    const payload = await response.json()
    statusPayload.value = payload
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown status error.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStatus()
})
</script>
