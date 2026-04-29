<template>
  <div class="primary-filters-card">
    <div class="board-mode-row">
      <div class="board-mode-toggle" role="tablist" aria-label="Job board mode">
        <button
          type="button"
          class="mode-button"
          :class="{ active: boardMode === 'search' }"
          @click="$emit('set-board-mode', 'search')"
        >
          Search jobs
        </button>
        <button
          type="button"
          class="mode-button"
          :class="{ active: boardMode === 'saved' }"
          @click="$emit('set-board-mode', 'saved')"
        >
          Saved jobs
        </button>
      </div>

      <label class="inline-select">
        <span>Items per page</span>
        <select
          :value="pageSize"
          name="job_page_size"
          autocomplete="off"
          @keydown.enter.prevent="$emit('run-enter-submit')"
          @change="$emit('set-page-size', Number($event.target.value))"
        >
          <option v-for="option in pageSizeOptions" :key="option" :value="option">
            {{ option }}
          </option>
        </select>
      </label>
    </div>

    <div v-if="boardMode === 'search'" class="primary-grid">
      <div class="primary-group primary-group-wide">
        <label for="job-keyword">Keyword</label>
        <input
          id="job-keyword"
          name="job_keyword"
          v-model.trim="draftFilters.keyword"
          type="text"
          autocomplete="off"
          autocapitalize="none"
          autocorrect="off"
          spellcheck="false"
          placeholder="Job title, company, skill, or keyword"
          @keydown.enter.prevent="$emit('run-enter-submit')"
        />

        <div class="company-selector">
          <label for="job-company-input">Companies</label>
          <input
            id="job-company-input"
            :value="companyInput"
            name="job_company_input"
            type="text"
            autocomplete="off"
            autocapitalize="none"
            autocorrect="off"
            spellcheck="false"
            placeholder="Start typing company names"
            @focus="$emit('open-company-menu')"
            @input="$emit('update-company-input', $event.target.value)"
            @blur="$emit('close-company-menu')"
            @keydown.enter.prevent="$emit('choose-company-from-input')"
            @keydown.down.prevent="$emit('move-company-selection', 1)"
            @keydown.up.prevent="$emit('move-company-selection', -1)"
            @keydown.esc.prevent="$emit('close-company-menu', true)"
          />

          <div
            v-if="showCompanyMenu"
            class="company-suggestions"
            role="listbox"
            aria-label="Company suggestions"
          >
            <button
              v-for="(option, index) in filteredCompanyOptions"
              :key="option.value"
              type="button"
              class="company-option"
              :class="{ active: index === companyActiveIndex }"
              @mousedown.prevent="$emit('add-company', option.value)"
            >
              <span>{{ option.value }}</span>
              <span v-if="option.observedCount" class="company-count">{{ option.observedCount }}</span>
            </button>
          </div>

          <p class="location-caption">Start typing to pick relevant companies, or press Enter to add an exact name.</p>

          <div class="chip-list" v-if="draftFilters.companies.length">
            <button
              class="chip"
              type="button"
              v-for="company in draftFilters.companies"
              :key="company"
              @click="$emit('remove-company', company)"
              :title="`Remove ${company}`"
            >
              {{ company }} x
            </button>
          </div>
        </div>
      </div>

      <div class="primary-group">
        <label>Location</label>
        <div class="mode-row">
          <button
            type="button"
            class="mode-button"
            :class="{ active: draftFilters.locationMode === 'country' }"
            @click="$emit('set-location-mode', 'country')"
          >
            Country
          </button>
          <button
            type="button"
            class="mode-button"
            :class="{ active: draftFilters.locationMode === 'nearby' }"
            @click="$emit('set-location-mode', 'nearby')"
          >
            Nearby
          </button>
          <button
            type="button"
            class="mode-button"
            :class="{ active: draftFilters.locationMode === 'manual' }"
            @click="$emit('set-location-mode', 'manual')"
          >
            Custom
          </button>
        </div>

        <div class="location-panel" v-if="draftFilters.locationMode === 'country'">
          <select
            id="job-country-code-primary"
            name="job_country_code_primary"
            autocomplete="off"
            v-model="draftFilters.countryCode"
            @keydown.enter.prevent="$emit('run-enter-submit')"
          >
            <option v-for="country in countryOptions" :key="country.code" :value="country.code">
              {{ country.name }}
            </option>
          </select>
          <p class="location-caption">Start broad across {{ currentCountryLabel }} and narrow only if needed.</p>
        </div>

        <div class="location-panel" v-else-if="draftFilters.locationMode === 'nearby'">
          <button type="button" class="secondary-action" @click="$emit('use-nearby')" :disabled="locationBusy">
            {{ locationBusy ? 'Finding your location…' : 'Use current location' }}
          </button>
          <p v-if="resolvedLocationLabel" class="location-caption">{{ resolvedLocationLabel }}</p>
          <p v-else class="location-caption">Opt in when you want nearby results instead of country-wide ones.</p>
        </div>

        <div class="location-panel" v-else>
          <input
            id="job-location-query"
            name="job_location_query"
            v-model.trim="draftFilters.manualLocationQuery"
            type="text"
            autocomplete="off"
            autocapitalize="none"
            autocorrect="off"
            spellcheck="false"
            placeholder="City or ZIP code"
            @keydown.enter.prevent="$emit('run-enter-submit')"
          />
          <p class="location-caption">Enter a place when you want a focused radius search.</p>
        </div>
      </div>

      <div class="primary-group">
        <label>Work setup</label>
        <div class="mode-row">
          <button
            type="button"
            class="mode-button"
            :class="{ active: draftFilters.includeRemote }"
            @click="draftFilters.includeRemote = !draftFilters.includeRemote"
          >
            Remote {{ draftFilters.includeRemote ? 'On' : 'Off' }}
          </button>
          <button
            type="button"
            class="mode-button"
            :class="{ active: draftFilters.includeHybrid }"
            @click="draftFilters.includeHybrid = !draftFilters.includeHybrid"
          >
            Hybrid {{ draftFilters.includeHybrid ? 'On' : 'Off' }}
          </button>
        </div>
        <p class="location-caption">Use these as straight switches for the kinds of roles you want included.</p>

        <div class="stacked-control">
          <label for="job-date-preset-primary">Posted</label>
          <select
            id="job-date-preset-primary"
            name="job_date_preset_primary"
            autocomplete="off"
            v-model="draftFilters.datePreset"
            @keydown.enter.prevent="$emit('run-enter-submit')"
          >
            <option value="any">Any time</option>
            <option value="today">Today</option>
            <option value="3">Past 3 days</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="custom">After date</option>
          </select>
        </div>

        <div class="stacked-control" v-if="draftFilters.datePreset === 'custom'">
          <label for="job-custom-date-primary">After date</label>
          <input
            id="job-custom-date-primary"
            name="job_custom_after_date_primary"
            v-model="draftFilters.customAfterDate"
            type="date"
            autocomplete="off"
            @keydown.enter.prevent="$emit('run-enter-submit')"
          />
        </div>
      </div>
    </div>

    <div v-if="boardMode === 'search'" class="primary-actions">
      <button type="button" class="primary-action" @click="$emit('apply')" :disabled="loading">
        {{ loading ? 'Searching…' : 'Search jobs' }}
      </button>
      <button type="button" class="secondary-action" @click="$emit('reset')" :disabled="loading">
        Reset
      </button>
      <button type="button" class="secondary-action" @click="$emit('toggle-advanced')" :disabled="loading">
        {{ advancedFiltersOpen ? 'Hide advanced filters' : 'Show advanced filters' }}
      </button>
    </div>

    <div v-else class="saved-mode-panel">
      <p class="saved-mode-copy">Saved jobs stay simple here for now. A richer saved-jobs subpage with better filtering is planned next.</p>
    </div>

    <p v-if="boardMode === 'search' && locationInfo" class="info-text">{{ locationInfo }}</p>
    <p v-if="boardMode === 'search' && locationWarning" class="warn-text">{{ locationWarning }}</p>
    <p v-if="boardMode === 'search' && locationError" class="error-text">{{ locationError }}</p>
  </div>
</template>

<script>
export default {
  name: 'JobBoardPrimaryFilters',
  props: {
    draftFilters: {
      type: Object,
      required: true,
    },
    boardMode: {
      type: String,
      default: 'search',
    },
    countryOptions: {
      type: Array,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
    locationBusy: {
      type: Boolean,
      default: false,
    },
    resolvedLocation: {
      type: Object,
      default: null,
    },
    locationInfo: {
      type: String,
      default: '',
    },
    locationWarning: {
      type: String,
      default: '',
    },
    locationError: {
      type: String,
      default: '',
    },
    advancedFiltersOpen: {
      type: Boolean,
      default: false,
    },
    pageSize: {
      type: Number,
      default: 10,
    },
    pageSizeOptions: {
      type: Array,
      default: () => [10, 20, 50, 100],
    },
    companyInput: {
      type: String,
      default: '',
    },
    filteredCompanyOptions: {
      type: Array,
      default: () => [],
    },
    showCompanyMenu: {
      type: Boolean,
      default: false,
    },
    companyActiveIndex: {
      type: Number,
      default: 0,
    },
  },
  emits: [
    'apply',
    'reset',
    'set-location-mode',
    'toggle-advanced',
    'use-nearby',
    'set-board-mode',
    'set-page-size',
    'update-company-input',
    'open-company-menu',
    'close-company-menu',
    'choose-company-from-input',
    'move-company-selection',
    'add-company',
    'remove-company',
    'run-enter-submit',
  ],
  computed: {
    currentCountryLabel() {
      const match = (this.countryOptions || []).find((country) => country.code === this.draftFilters.countryCode)
      return match?.name || this.draftFilters.countryCode || 'your country'
    },
    resolvedLocationLabel() {
      const city = this.resolvedLocation?.city || this.resolvedLocation?.display_name || ''
      const code = this.resolvedLocation?.country_code ? ` (${this.resolvedLocation.country_code})` : ''
      return city ? `Using ${city}${code}` : ''
    },
  },
}
</script>

<style scoped>
.primary-filters-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.95));
  padding: 18px;
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.05);
}

.board-mode-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.board-mode-toggle,
.mode-row,
.primary-actions,
.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.inline-select {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
}

.inline-select select {
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 9px 11px;
  background: #ffffff;
  min-width: 92px;
}

.primary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.primary-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.primary-group-wide {
  grid-column: span 2;
}

.primary-group label,
.stacked-control label {
  font-size: 0.84rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: #334155;
}

.primary-group input,
.primary-group select,
.stacked-control input,
.stacked-control select {
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 11px 12px;
  font-size: 0.95rem;
  background: #ffffff;
  min-width: 0;
}

.primary-group input:focus,
.primary-group select:focus,
.stacked-control input:focus,
.stacked-control select:focus,
.inline-select select:focus {
  outline: 2px solid rgba(37, 99, 235, 0.16);
  border-color: var(--color-primary-600);
}

.company-selector,
.location-panel,
.stacked-control,
.saved-mode-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.company-selector {
  position: relative;
  margin-top: 4px;
}

.company-suggestions {
  position: absolute;
  z-index: 20;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #cfd7df;
  border-radius: 10px;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.09);
  padding: 4px;
  max-height: 240px;
  overflow-y: auto;
}

.company-option {
  width: 100%;
  border: none;
  background: transparent;
  border-radius: 8px;
  padding: 8px 10px;
  color: #1f2937;
  cursor: pointer;
  font-size: 0.9rem;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.company-option:hover,
.company-option.active {
  background: rgba(37, 99, 235, 0.12);
}

.company-count {
  color: #64748b;
  font-size: 0.8rem;
}

.mode-button,
.secondary-action,
.primary-action,
.chip {
  border-radius: 999px;
  border: 1px solid #cbd5e1;
  padding: 8px 14px;
  font-size: 0.9rem;
  cursor: pointer;
}

.mode-button,
.secondary-action,
.chip {
  background: #ffffff;
  color: #1f2937;
}

.mode-button.active {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
  color: #ffffff;
}

.primary-action {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
  color: #ffffff;
}

.primary-actions {
  margin-top: 16px;
}

.location-caption,
.info-text,
.warn-text,
.error-text,
.saved-mode-copy {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.45;
}

.location-caption,
.info-text,
.saved-mode-copy {
  color: #475569;
}

.saved-mode-panel {
  border-top: 1px solid rgba(148, 163, 184, 0.18);
  padding-top: 16px;
}

.warn-text {
  color: #9a6700;
  margin-top: 10px;
}

.error-text {
  color: #b91c1c;
  margin-top: 10px;
}

@media (max-width: 860px) {
  .primary-group-wide {
    grid-column: span 1;
  }
}

@media (max-width: 700px) {
  .board-mode-row {
    flex-direction: column;
    align-items: stretch;
  }

  .inline-select {
    width: 100%;
    justify-content: space-between;
  }

  .inline-select select {
    flex: 1;
  }
}

@media (max-width: 600px) {
  .primary-filters-card {
    padding: 14px;
  }

  .primary-grid,
  .primary-actions,
  .board-mode-toggle,
  .mode-row,
  .chip-list {
    gap: 10px;
  }

  .mode-button,
  .secondary-action,
  .primary-action {
    width: 100%;
    text-align: center;
  }
}

</style>

<style>
html[data-theme="dark"] .primary-filters-card {
  border-color: var(--border-color);
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--color-surface-muted) 90%, black),
    var(--color-surface)
  );
  color: var(--color-text-primary);
}

html[data-theme="dark"] .inline-select {
  color: var(--color-text-secondary);
}

html[data-theme="dark"] .inline-select select,
html[data-theme="dark"] .primary-group input,
html[data-theme="dark"] .primary-group select,
html[data-theme="dark"] .stacked-control input,
html[data-theme="dark"] .stacked-control select {
  background: var(--color-surface-muted);
  border-color: var(--border-color);
  color: var(--color-text-primary);
}

html[data-theme="dark"] .primary-group input:focus,
html[data-theme="dark"] .primary-group select:focus,
html[data-theme="dark"] .stacked-control input:focus,
html[data-theme="dark"] .stacked-control select:focus,
html[data-theme="dark"] .inline-select select:focus {
  outline: 2px solid rgba(96, 165, 250, 0.45);
  border-color: rgba(96, 165, 250, 0.72);
}

html[data-theme="dark"] .primary-group input::placeholder,
html[data-theme="dark"] .stacked-control input::placeholder {
  color: var(--color-text-muted);
}

html[data-theme="dark"] .primary-group label,
html[data-theme="dark"] .stacked-control label {
  color: var(--color-text-secondary);
}

html[data-theme="dark"] .company-suggestions {
  background: var(--color-surface);
  border-color: var(--border-color);
}

html[data-theme="dark"] .company-option {
  color: var(--color-text-primary);
}

html[data-theme="dark"] .company-option:hover,
html[data-theme="dark"] .company-option.active {
  background: rgba(59, 130, 246, 0.24);
}

html[data-theme="dark"] .company-count {
  color: var(--color-text-secondary);
}

html[data-theme="dark"] .mode-button,
html[data-theme="dark"] .secondary-action,
html[data-theme="dark"] .chip {
  background: var(--color-surface);
  border-color: var(--border-color);
  color: var(--color-text-primary);
}

html[data-theme="dark"] .saved-mode-panel {
  border-top-color: var(--border-color);
}

html[data-theme="dark"] .location-caption,
html[data-theme="dark"] .info-text,
html[data-theme="dark"] .saved-mode-copy {
  color: var(--color-text-secondary);
}
</style>
