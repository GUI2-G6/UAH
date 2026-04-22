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

        <p v-if="refreshNote" class="status-refresh-note" role="status" aria-live="polite">
          {{ refreshNote }}
        </p>

        <div class="status-actions">
          <button class="button-secondary" type="button" @click="loadStatus(true)" :disabled="loading">
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
import { messageFromApiFailure } from '../lib/apiErrorMessage.js'

const loading = ref(true)
const error = ref('')
const refreshNote = ref('')
const lastManualRefreshAt = ref(0)
const MIN_MS_BETWEEN_MANUAL_REFRESH = 3500
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

async function loadStatus(fromUser = false) {
  if (fromUser) {
    const now = Date.now()
    if (now - lastManualRefreshAt.value < MIN_MS_BETWEEN_MANUAL_REFRESH) {
      refreshNote.value =
        'Please wait a few seconds between refreshes. This keeps the page gentle on the status service.'
      return
    }
    lastManualRefreshAt.value = now
  }
  refreshNote.value = ''
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/status')
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      const msg = messageFromApiFailure(response, payload)
      throw new Error(msg || `Status endpoint returned HTTP ${response.status}.`)
    }
    const contentType = response.headers?.get?.('content-type') || ''
    if (contentType && !contentType.includes('application/json')) {
      const bodyPreview =
        typeof response.text === 'function' ? (await response.text()).slice(0, 120).trim() : ''
      const looksLikeHtml = bodyPreview.startsWith('<')
      if (looksLikeHtml) {
        throw new Error(
          `Status endpoint returned HTML instead of JSON (HTTP ${response.status}). Check /api proxy configuration.`
        )
      }
      throw new Error(
        `Status endpoint did not return JSON (HTTP ${response.status}, content-type: ${contentType}).`
      )
    }
    let payload
    try {
      payload = await response.json()
    } catch {
      throw new Error(`Status endpoint returned invalid JSON (HTTP ${response.status}).`)
    }
    statusPayload.value = payload
  } catch (err) {
    if (err instanceof TypeError) {
      error.value = messageFromApiFailure({ status: 0 }, null)
    } else {
      error.value = err instanceof Error ? err.message : 'Unknown status error.'
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStatus(false)
})
</script>

<style scoped>
.status-refresh-note {
  margin: 0.5rem 0 0;
  font-size: 0.9rem;
  line-height: 1.45;
  color: #7a4e00;
}
</style>
