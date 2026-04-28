<template>
  <section class="legacy-bridge">
    <div class="legacy-bridge-card">
      <p class="legacy-label">Status moved</p>
      <h1>This page moved to the public landing</h1>
      <p>
        Status now lives on the dedicated public landing page so the update stream and transparency docs stay in one
        place.
      </p>
      <p>Choose how you want to continue.</p>
      <div class="legacy-actions">
        <button class="submit-btn" type="button" @click="openInNewTab">Open status in new tab</button>
        <button class="landing-btn" type="button" @click="openHere">Open status here</button>
      </div>
    </div>
  </section>
</template>

<script>
import { showToast } from '@/services/toastService.js'

const DEFAULT_PUBLIC_LANDING_URL = 'https://uahapp.com'

export default {
  name: 'StatusBridge',
  data() {
    return {
      destination: `${DEFAULT_PUBLIC_LANDING_URL}/status`,
    }
  },
  created() {
    const configuredBase = String(import.meta.env.VITE_PUBLIC_LANDING_URL || '').trim()
    const base = (configuredBase || DEFAULT_PUBLIC_LANDING_URL).replace(/\/+$/, '')
    this.destination = `${base}/status`
  },
  methods: {
    openInNewTab() {
      window.open(this.destination, '_blank', 'noopener,noreferrer')
      showToast('Status opened in a new tab.', 'success')
    },
    openHere() {
      window.location.replace(this.destination)
    },
  },
}
</script>

<style scoped>
.legacy-bridge {
  min-height: 62vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
}

.legacy-bridge-card {
  width: min(660px, 100%);
  border: 1px solid var(--border-color);
  border-radius: 18px;
  padding: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--shadow-card);
  display: grid;
  gap: 12px;
}

.legacy-label {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--color-text-muted);
}

h1 {
  margin: 0;
  font-size: clamp(1.6rem, 3vw, 2rem);
}

p {
  margin: 0;
  color: var(--color-text-secondary);
}

.legacy-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 6px;
}

.submit-btn,
.landing-btn {
  border: 1px solid var(--border-color);
  border-radius: 999px;
  padding: 10px 16px;
  background: #ffffff;
  color: var(--color-text-primary);
  font-weight: 600;
}

@media (max-width: 640px) {
  .legacy-actions {
    flex-direction: column;
  }
}
</style>
