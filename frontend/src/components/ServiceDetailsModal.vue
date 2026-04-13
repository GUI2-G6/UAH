<template>
  <div
    class="service-details-overlay"
    role="dialog"
    aria-modal="true"
    :aria-label="service?.label || 'Service details'"
    @click="close"
  >
    <div class="service-details-dialog" v-draggable-modal="{ handle: '.service-details-header' }" @click.stop>
      <div class="service-details-header drag-handle">
        <div class="service-details-hero">
          <div class="service-details-chip" :class="chipClass">
            {{ monogram }}
          </div>
          <div class="service-details-heading">
            <p class="service-details-eyebrow">Service connection</p>
            <h2>{{ service?.label || 'Loading service' }}</h2>
            <p class="service-details-subtitle">
              {{ service?.description || 'Preparing connection details…' }}
            </p>
          </div>
        </div>
        <button type="button" class="service-details-close" @click="close">Close</button>
      </div>

      <div class="service-details-body">
        <div class="service-details-status-row">
          <span class="service-details-badge" :class="badgeClass">
            {{ statusLabel }}
          </span>
          <span v-if="service?.account_label" class="service-details-account">
            {{ service.account_label }}
          </span>
        </div>

        <p v-if="error" class="service-details-error">{{ error }}</p>
        <p v-if="loading" class="service-details-loading">Loading service details…</p>

        <template v-else-if="service">
          <section class="service-details-section">
            <h3>Why connect this</h3>
            <p>{{ service.description }}</p>
          </section>

          <section class="service-details-section">
            <h3>What UAH can use it for</h3>
            <ul>
              <li v-for="capability in service.capabilities || []" :key="capability">{{ capability }}</li>
            </ul>
          </section>

          <section class="service-details-section">
            <h3>What access is requested</h3>
            <ul>
              <li v-for="permission in service.permissions || []" :key="permission">{{ permission }}</li>
            </ul>
          </section>

          <section class="service-details-section">
            <h3>Current status</h3>
            <p class="service-details-readiness-title">{{ service.readiness?.title || 'Service status' }}</p>
            <p>{{ service.readiness?.description || 'No readiness details available yet.' }}</p>
          </section>

          <section v-if="(service.planned_features || []).length" class="service-details-section">
            <h3>Planned features</h3>
            <ul>
              <li v-for="feature in service.planned_features || []" :key="feature">{{ feature }}</li>
            </ul>
          </section>
        </template>
      </div>

      <div class="service-details-actions">
        <button
          v-for="action in service?.actions || []"
          :key="`${service?.key || 'service'}-${action.key}`"
          type="button"
          class="service-details-action"
          :class="`is-${action.style || 'secondary'}`"
          :disabled="loading || !action.enabled || busyActionKey === `${service?.key || ''}:${action.key}`"
          @click="$emit('action', action)"
        >
          {{ actionLabel(action) }}
        </button>
        <button type="button" class="service-details-action is-ghost" @click="close">Close</button>
      </div>
    </div>
  </div>
</template>

<script>
const STATUS_LABELS = {
  connected: 'Connected',
  available: 'Available',
  coming_soon: 'Coming soon',
  needs_attention: 'Needs attention',
}

const MONOGRAMS = {
  gmail: 'GM',
  calendar_sync: 'CS',
  resume_imports: 'RI',
}

export default {
  name: 'ServiceDetailsModal',
  props: {
    service: {
      type: Object,
      default: null,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    error: {
      type: String,
      default: '',
    },
    busyActionKey: {
      type: String,
      default: '',
    },
  },
  emits: ['close', 'action'],
  computed: {
    statusLabel() {
      const status = this.service?.status || 'available'
      return STATUS_LABELS[status] || 'Available'
    },
    badgeClass() {
      const status = this.service?.status || 'available'
      return `is-${status.replaceAll('_', '-')}`
    },
    chipClass() {
      const key = String(this.service?.key || 'service').replaceAll('_', '-')
      return `is-${key}`
    },
    monogram() {
      return MONOGRAMS[this.service?.key] || 'SV'
    },
  },
  mounted() {
    this._onKeyDown = (event) => {
      if (event.key === 'Escape') {
        this.close()
      }
    }
    window.addEventListener('keydown', this._onKeyDown)
  },
  beforeUnmount() {
    if (this._onKeyDown) {
      window.removeEventListener('keydown', this._onKeyDown)
    }
  },
  methods: {
    close() {
      this.$emit('close')
    },
    actionLabel(action) {
      const actionKey = `${this.service?.key || ''}:${action.key}`
      if (this.busyActionKey !== actionKey) return action.label
      if (action.key === 'connect') return 'Connecting…'
      if (action.key === 'disconnect') return 'Disconnecting…'
      return 'Working…'
    },
  },
}
</script>

<style scoped>
.service-details-overlay {
  position: fixed;
  inset: 0;
  z-index: 10020;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  background: rgba(15, 23, 42, 0.55);
}

.service-details-dialog {
  width: min(760px, 96vw);
  max-height: 88vh;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 26px 60px rgba(15, 23, 42, 0.24);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.service-details-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 20px 22px 16px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  cursor: grab;
}

.service-details-hero {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
}

.service-details-chip {
  width: 54px;
  height: 54px;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #7f1d1d;
  background: linear-gradient(135deg, rgba(248, 113, 113, 0.18), rgba(254, 226, 226, 0.92));
  border: 1px solid rgba(239, 68, 68, 0.18);
  flex-shrink: 0;
}

.service-details-chip.is-calendar-sync {
  color: #1d4ed8;
  background: linear-gradient(135deg, rgba(96, 165, 250, 0.2), rgba(219, 234, 254, 0.95));
  border-color: rgba(59, 130, 246, 0.22);
}

.service-details-chip.is-resume-imports {
  color: #0f766e;
  background: linear-gradient(135deg, rgba(45, 212, 191, 0.2), rgba(204, 251, 241, 0.96));
  border-color: rgba(13, 148, 136, 0.24);
}

.service-details-heading {
  min-width: 0;
}

.service-details-eyebrow {
  margin: 0 0 4px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.service-details-heading h2 {
  margin: 0;
  font-size: 1.28rem;
  color: #111827;
}

.service-details-subtitle {
  margin: 8px 0 0;
  color: #475569;
  line-height: 1.55;
}

.service-details-close,
.service-details-action {
  border: 1px solid rgba(148, 163, 184, 0.42);
  border-radius: 10px;
  background: #ffffff;
  color: #1f2937;
  cursor: pointer;
  font-weight: 600;
}

.service-details-close {
  padding: 10px 14px;
}

.service-details-body {
  padding: 18px 22px;
  overflow: auto;
  display: grid;
  gap: 14px;
}

.service-details-status-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.service-details-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 0.78rem;
  font-weight: 700;
  border: 1px solid transparent;
}

.service-details-badge.is-connected {
  color: #166534;
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(22, 101, 52, 0.28);
}

.service-details-badge.is-available {
  color: #0f172a;
  background: rgba(148, 163, 184, 0.16);
  border-color: rgba(100, 116, 139, 0.26);
}

.service-details-badge.is-coming-soon {
  color: #7c2d12;
  background: rgba(251, 191, 36, 0.16);
  border-color: rgba(180, 83, 9, 0.26);
}

.service-details-badge.is-needs-attention {
  color: #9a3412;
  background: rgba(251, 146, 60, 0.16);
  border-color: rgba(194, 65, 12, 0.25);
}

.service-details-account {
  color: #475569;
  font-size: 0.9rem;
  overflow-wrap: anywhere;
}

.service-details-error,
.service-details-loading {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.2);
  color: #334155;
}

.service-details-error {
  border-color: rgba(239, 68, 68, 0.22);
  color: #991b1b;
}

.service-details-section {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  padding: 14px 16px;
}

.service-details-section h3 {
  margin: 0 0 8px;
  font-size: 0.98rem;
  color: #111827;
}

.service-details-section p,
.service-details-section li {
  color: #475569;
  line-height: 1.55;
}

.service-details-section p {
  margin: 0;
}

.service-details-section ul {
  margin: 0;
  padding-left: 18px;
}

.service-details-section li + li {
  margin-top: 8px;
}

.service-details-readiness-title {
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
}

.service-details-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 22px 20px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(248, 250, 252, 0.92);
}

.service-details-action {
  min-width: 120px;
  padding: 10px 14px;
}

.service-details-action:disabled {
  opacity: 0.65;
  cursor: default;
}

.service-details-action.is-primary {
  background: #111827;
  color: #ffffff;
  border-color: #111827;
}

.service-details-action.is-secondary {
  background: rgba(226, 232, 240, 0.7);
}

.service-details-action.is-muted,
.service-details-action.is-ghost {
  background: #ffffff;
}

@media (max-width: 720px) {
  .service-details-overlay {
    padding: 12px;
  }

  .service-details-header {
    flex-direction: column;
    align-items: stretch;
  }

  .service-details-hero {
    align-items: center;
  }

  .service-details-actions {
    justify-content: stretch;
  }

  .service-details-action,
  .service-details-close {
    width: 100%;
  }
}
</style>
