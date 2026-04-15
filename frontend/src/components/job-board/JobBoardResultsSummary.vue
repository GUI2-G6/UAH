<template>
  <section class="results-summary-card">
    <div class="results-summary-top">
      <div>
        <p class="eyebrow">{{ boardMode === 'saved' ? 'Saved jobs' : 'Search summary' }}</p>
        <h2 v-if="loading">Refreshing results…</h2>
        <h2 v-else-if="error">{{ error }}</h2>
        <h2 v-else>{{ headline }}</h2>
        <p v-if="!error" class="summary-copy">{{ summaryCopy }}</p>
      </div>

      <div v-if="boardMode !== 'saved'" class="summary-actions">
        <label v-if="!error" class="sort-control">
          <span>Sort</span>
          <select
            :value="sortBy"
            name="job_sort"
            autocomplete="off"
            :disabled="loading"
            @change="$emit('sort-change', $event.target.value)"
          >
            <option v-for="option in sortOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <button type="button" class="secondary-action" @click="$emit('clear')" :disabled="loading">
          Reset
        </button>
        <button v-if="canWidenSearch" type="button" class="primary-action" @click="$emit('widen')" :disabled="loading">
          Widen search
        </button>
      </div>
    </div>

    <div v-if="boardMode !== 'saved' && activeFilterChips.length" class="active-filter-chip-list">
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
    boardMode: {
      type: String,
      default: 'search',
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
    sortBy: {
      type: String,
      default: 'date_desc',
    },
    sortOptions: {
      type: Array,
      default: () => [],
    },
    savedModeNote: {
      type: String,
      default: '',
    },
  },
  emits: ['clear', 'remove-chip', 'sort-change', 'widen'],
  computed: {
    headline() {
      if (this.boardMode === 'saved') {
        if (this.totalJobs > 0) {
          return `Showing ${this.jobsLength} saved jobs on page ${this.page} of ${this.totalJobs}`
        }
        if (this.jobsLength > 0) {
          return `Showing ${this.jobsLength} saved jobs`
        }
        return 'No saved jobs yet'
      }
      if (this.totalJobs > 0) {
        const totalLabel = this.totalsAreEstimated ? `about ${this.totalJobs}` : `${this.totalJobs}`
        return `Showing ${this.jobsLength} jobs on page ${this.page} of ${totalLabel}`
      }
      if (this.jobsLength > 0) {
        return `Showing ${this.jobsLength} jobs on page ${this.page}`
      }
      return 'No jobs matched that search yet'
    },
    summaryCopy() {
      if (this.boardMode === 'saved') {
        return this.savedModeNote || 'Saved jobs stay simple for now while a richer saved-jobs board is planned.'
      }
      return this.searchScopeSummary
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

.results-summary-top > div:first-child {
  min-width: 0;
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
  align-items: center;
  justify-content: flex-end;
  min-width: 0;
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

.sort-control {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
}

.sort-control select {
  max-width: 100%;
  min-height: 36px;
  border: 1px solid rgba(203, 213, 225, 0.95);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.96);
  padding: 8px 10px;
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
  .summary-actions button,
  .sort-control,
  .sort-control select {
    width: 100%;
  }
}
</style>
