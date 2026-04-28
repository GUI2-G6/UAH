<template>
  <article class="application-item">
    <header class="application-item-header">
      <h3>{{ application.company || 'Unknown company' }}</h3>
      <p class="application-status-chip" :class="`is-${statusTone}`">{{ readableStatus }}</p>
    </header>
    <p class="application-role">{{ application.role || 'Untitled role' }}</p>
    <p class="application-meta">{{ application.from || 'Unknown sender' }}</p>
    <p class="application-meta">{{ formattedDate }}</p>
    <p v-if="application.snippet" class="application-snippet">{{ application.snippet }}</p>
  </article>
</template>

<script>
export default {
  name: "Application",
  props: {
    application: {
      type: Object,
      default: () => ({}),
    }
  },
  computed: {
    readableStatus() {
      const raw = String(this.application.status || this.application.detected_status || 'unknown')
      return raw.replaceAll('_', ' ')
    },
    statusTone() {
      const normalized = String(this.application.status || this.application.detected_status || '').toLowerCase()
      if (normalized.includes('offer')) return 'offer'
      if (normalized.includes('interview')) return 'interview'
      if (normalized.includes('rejection')) return 'rejection'
      if (normalized.includes('applied')) return 'applied'
      return 'unknown'
    },
    formattedDate() {
      const value = this.application.date
      if (!value) return 'Date unavailable'
      const date = new Date(value)
      return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
    },
  },
}
</script>

<style scoped>
.application-item {
  display: grid;
  gap: 7px;
}

.application-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.application-item-header h3 {
  margin: 0;
  font-size: 1rem;
  color: var(--color-text-primary);
}

.application-role,
.application-meta {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.92rem;
}

.application-snippet {
  margin: 2px 0 0;
  color: var(--color-text-primary);
  font-size: 0.93rem;
  line-height: 1.4;
}

.application-status-chip {
  margin: 0;
  font-size: 0.72rem;
  line-height: 1;
  padding: 7px 10px;
  border-radius: 999px;
  text-transform: capitalize;
  border: 1px solid var(--border-color);
  background: var(--color-surface-muted);
}

.application-status-chip.is-interview {
  color: var(--color-primary-600);
  border-color: rgba(37, 99, 235, 0.35);
}

.application-status-chip.is-offer {
  color: var(--color-success-600);
  border-color: rgba(22, 163, 74, 0.35);
}

.application-status-chip.is-rejection {
  color: var(--color-danger-600);
  border-color: rgba(220, 38, 38, 0.35);
}
</style>