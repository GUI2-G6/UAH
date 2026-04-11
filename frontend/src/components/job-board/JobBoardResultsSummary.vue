<template>
  <section class="results-summary-card">
    <div class="results-summary-top">
      <div>
        <p class="eyebrow">Search summary</p>
        <h2 v-if="loading">Refreshing results…</h2>
        <h2 v-else-if="error">{{ error }}</h2>
        <h2 v-else>{{ headline }}</h2>
        <p v-if="!error" class="summary-copy">{{ searchScopeSummary }}</p>
      </div>

      <div class="summary-actions">
        <button type="button" class="secondary-action" @click="$emit('clear')" :disabled="loading">
          Reset
        </button>
        <button v-if="canWidenSearch" type="button" class="primary-action" @click="$emit('widen')" :disabled="loading">
          Widen search
        </button>
      </div>
    </div>

    <div v-if="activeFilterChips.length" class="active-filter-chip-list">
      <button
        type="button"
        class="active-filter-chip"
        v-for="chip in activeFilterChips"
        :key="chip.key"
        :title="`Remove ${chip.label}`"
        @click="$emit('remove-chip', chip)"
      >
        {{ chip.label }} x
      </button>
    </div>

    <p v-if="compatibilityNotice" class="note-text">{{ compatibilityNotice }}</p>
    <p v-if="locationLimitNotice" class="warn-text">{{ locationLimitNotice }}</p>
  </section>
</template>

<script>
export default {
  name: 'JobBoardResultsSummary',
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
    error: {
      type: String,
      default: '',
    },
    jobsLength: {
      type: Number,
      default: 0,
    },
    totalJobs: {
      type: Number,
      default: 0,
    },
    totalsAreEstimated: {
      type: Boolean,
      default: false,
    },
    page: {
      type: Number,
      default: 1,
    },
    searchScopeSummary: {
      type: String,
      default: '',
    },
    activeFilterChips: {
      type: Array,
      default: () => [],
    },
    compatibilityNotice: {
      type: String,
      default: '',
    },
    locationLimitNotice: {
      type: String,
      default: '',
    },
    canWidenSearch: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['clear', 'remove-chip', 'widen'],
  computed: {
    headline() {
      if (this.totalJobs > 0) {
        const totalLabel = this.totalsAreEstimated ? `about ${this.totalJobs}` : `${this.totalJobs}`
        return `Showing ${this.jobsLength} jobs on page ${this.page} of ${totalLabel}`
      }
      if (this.jobsLength > 0) {
        return `Showing ${this.jobsLength} jobs on page ${this.page}`
      }
      return 'No jobs matched that search yet'
    },
  },
}
</script>

<style scoped>
.results-summary-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: #ffffff;
  padding: 18px;
  margin: 16px 16px 0;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.results-summary-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

h2 {
  margin: 0;
  font-size: 1.15rem;
  color: #0f172a;
}

.summary-copy,
.note-text,
.warn-text {
  margin: 8px 0 0;
  line-height: 1.5;
  font-size: 0.92rem;
}

.summary-copy,
.note-text {
  color: #475569;
}

.warn-text {
  color: #9a6700;
}

.summary-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.secondary-action,
.primary-action,
.active-filter-chip {
  border-radius: 999px;
  border: 1px solid #cbd5e1;
  padding: 8px 14px;
  cursor: pointer;
}

.secondary-action,
.active-filter-chip {
  background: #ffffff;
  color: #1f2937;
}

.primary-action {
  background: #0f766e;
  border-color: #0f766e;
  color: #ffffff;
}

.active-filter-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

@media (max-width: 700px) {
  .results-summary-card {
    margin: 14px 12px 0;
    padding: 14px;
  }

  .results-summary-top {
    flex-direction: column;
  }

  .summary-actions,
  .summary-actions button {
    width: 100%;
  }
}
</style>
