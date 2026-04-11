<template>
  <div class="primary-filters-card">
    <div class="primary-grid">
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
        />
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
          <select id="job-country-code-primary" name="job_country_code_primary" autocomplete="off" v-model="draftFilters.countryCode">
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
        <p class="location-caption">Both stay on by default so the first search feels broad instead of cramped.</p>
      </div>
    </div>

    <div class="primary-actions">
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

    <p v-if="locationInfo" class="info-text">{{ locationInfo }}</p>
    <p v-if="locationWarning" class="warn-text">{{ locationWarning }}</p>
    <p v-if="locationError" class="error-text">{{ locationError }}</p>
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
  },
  emits: ['apply', 'reset', 'set-location-mode', 'toggle-advanced', 'use-nearby'],
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

.primary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.primary-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.primary-group-wide {
  grid-column: span 2;
}

.primary-group label {
  font-size: 0.84rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: #334155;
}

.primary-group input,
.primary-group select {
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 11px 12px;
  font-size: 0.95rem;
  background: #ffffff;
}

.primary-group input:focus,
.primary-group select:focus {
  outline: 2px solid rgba(37, 99, 235, 0.16);
  border-color: var(--color-primary-600);
}

.mode-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mode-button,
.secondary-action,
.primary-action {
  border-radius: 999px;
  border: 1px solid #cbd5e1;
  padding: 8px 14px;
  font-size: 0.9rem;
  cursor: pointer;
}

.mode-button,
.secondary-action {
  background: #ffffff;
  color: #1f2937;
}

.mode-button.active {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
  color: #ffffff;
}

.primary-action {
  background: #0f766e;
  border-color: #0f766e;
  color: #ffffff;
}

.primary-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.location-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.location-caption,
.info-text,
.warn-text,
.error-text {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.4;
}

.location-caption,
.info-text {
  color: #475569;
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

@media (max-width: 600px) {
  .primary-filters-card {
    padding: 14px;
  }

  .primary-grid,
  .primary-actions {
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
