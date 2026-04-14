<template>
    <div class="page job-board-page">
        <div class="greeting job-board-hero">
            <div>
                <h1>Job Board</h1>
                <p>Start broad, then narrow only when you need to.</p>
            </div>
            <div class="hero-copy">
                <p>{{ heroSearchCopy }}</p>
            </div>
        </div>

        <section class="filters job-board-filters">
            <JobBoardPrimaryFilters
              :draft-filters="draftFilters"
              :country-options="countryOptions"
              :loading="loading"
              :location-busy="locationBusy"
              :resolved-location="resolvedLocation"
              :location-info="locationInfo"
              :location-warning="locationWarning"
              :location-error="locationError"
              :advanced-filters-open="advancedFiltersOpen"
              @apply="applyFilters"
              @reset="clearFilters"
              @set-location-mode="setLocationMode"
              @toggle-advanced="advancedFiltersOpen = !advancedFiltersOpen"
              @use-nearby="activateNearbyMode"
            />

            <section v-if="advancedFiltersOpen" class="advanced-filters-panel">
                <div class="advanced-filters-header">
                    <div>
                        <p class="advanced-eyebrow">Advanced filters</p>
                        <h2>Optional narrowing</h2>
                    </div>
                    <p>Use these when you already know how you want to trim the search.</p>
                </div>

                <div class="filter-grid">
                    <div class="filter-group">
                        <label for="job-date-preset">Posted</label>
                        <select id="job-date-preset" name="job_date_preset" autocomplete="off" v-model="draftFilters.datePreset">
                            <option value="any">Any time</option>
                            <option value="today">Today</option>
                            <option value="3">Past 3 days</option>
                            <option value="7">Last 7 days</option>
                            <option value="30">Last 30 days</option>
                            <option value="custom">After date</option>
                        </select>
                    </div>

                    <div class="filter-group" v-if="draftFilters.datePreset === 'custom'">
                        <label for="job-custom-date">After date</label>
                        <input
                            id="job-custom-date"
                            name="job_custom_after_date"
                            v-model="draftFilters.customAfterDate"
                            type="date"
                            autocomplete="off"
                        />
                    </div>

                    <div class="filter-group">
                      <label for="job-categories">Categories</label>
                      <div class="category-selector">
                        <input
                          id="job-categories"
                          name="job_categories_input"
                          v-model.trim="categoryInput"
                          type="text"
                          autocomplete="off"
                          autocapitalize="none"
                          autocorrect="off"
                          spellcheck="false"
                          placeholder="Search categories"
                          @focus="openCategoryMenu"
                          @input="onCategoryInput"
                          @blur="closeCategoryMenuSoon"
                          @keydown.enter.prevent="chooseCategoryFromInput"
                          @keydown.down.prevent="moveCategorySelection(1)"
                          @keydown.up.prevent="moveCategorySelection(-1)"
                          @keydown.esc.prevent="categoryMenuOpen = false"
                        />

                        <div
                          v-if="showCategoryMenu"
                          class="category-suggestions"
                          role="listbox"
                          aria-label="Category suggestions"
                        >
                          <button
                            v-for="(option, index) in filteredCategoryOptions"
                            :key="option"
                            type="button"
                            class="category-option"
                            :class="{ active: index === categoryActiveIndex }"
                            @mousedown.prevent="addCategory(option)"
                          >
                            {{ option }}
                          </button>
                        </div>

                        <p class="hint-text" v-if="categoryInfo">{{ categoryInfo }}</p>
                        <p class="hint-text">Search suggested categories or add an exact category value and press Enter.</p>

                        <div class="chip-list" v-if="draftFilters.categories.length">
                          <button
                            class="chip"
                            type="button"
                            v-for="category in draftFilters.categories"
                            :key="category"
                            @click="removeFilterValue('categories', category)"
                            :title="`Remove ${category}`"
                          >
                            {{ category }} x
                          </button>
                        </div>
                      </div>
                    </div>

                    <div class="filter-group">
                        <label for="job-levels">Levels</label>
                        <div class="category-selector">
                          <input
                            id="job-levels"
                            name="job_levels_input"
                            v-model.trim="levelInput"
                            type="text"
                            autocomplete="off"
                            autocapitalize="none"
                            autocorrect="off"
                            spellcheck="false"
                            placeholder="Search experience levels"
                            @focus="openLevelMenu"
                            @input="onLevelInput"
                            @blur="closeLevelMenuSoon"
                            @keydown.enter.prevent="chooseLevelFromInput"
                            @keydown.down.prevent="moveLevelSelection(1)"
                            @keydown.up.prevent="moveLevelSelection(-1)"
                            @keydown.esc.prevent="levelMenuOpen = false"
                          />

                          <div
                            v-if="showLevelMenu"
                            class="category-suggestions"
                            role="listbox"
                            aria-label="Level suggestions"
                          >
                            <button
                              v-for="(option, index) in filteredLevelOptions"
                              :key="option.value"
                              type="button"
                              class="category-option"
                              :class="{ active: index === levelActiveIndex }"
                              @mousedown.prevent="addLevel(option.value)"
                            >
                              {{ option.label }}
                            </button>
                          </div>

                          <p class="hint-text" v-if="levelInfo">{{ levelInfo }}</p>

                          <div class="chip-list" v-if="draftFilters.levels.length">
                            <button
                              class="chip"
                              type="button"
                              v-for="level in draftFilters.levels"
                              :key="level"
                              @click="removeFilterValue('levels', level)"
                              :title="`Remove ${formatLevelLabel(level)}`"
                            >
                              {{ formatLevelLabel(level) }} x
                            </button>
                          </div>
                        </div>
                    </div>
                </div>

                <div class="filter-grid">
                    <div class="filter-group">
                        <label for="job-country-code">Country</label>
                        <select id="job-country-code" name="job_country_code" autocomplete="off" v-model="draftFilters.countryCode">
                          <option v-for="country in countryOptions" :key="country.code" :value="country.code">
                            {{ country.name }}{{ country.observed_count ? ` (${country.observed_count})` : '' }}
                          </option>
                        </select>
                        <p class="helper-text">Country mode stays broad. Nearby and custom location use this as a boundary when available.</p>
                    </div>

                    <div class="filter-group">
                        <label for="job-provider-filter">Source</label>
                        <select id="job-provider-filter" name="job_provider_filter" autocomplete="off" v-model="draftFilters.provider">
                          <option value="">All providers</option>
                          <option v-for="provider in providerOptions" :key="provider.value" :value="provider.value">
                            {{ provider.label }}{{ provider.observedCount ? ` (${provider.observedCount})` : "" }}
                          </option>
                        </select>
                        <p class="helper-text">Use one source when you want a tighter, provider-specific feed.</p>
                    </div>

                    <div class="filter-group" v-if="draftFilters.locationMode !== 'country'">
                        <label for="job-radius">Search radius</label>
                        <div class="radius-row">
                          <input
                            id="job-radius"
                            v-model.number="draftFilters.locationRadius"
                            type="range"
                            :min="1"
                            :max="maxRadiusForUnit"
                            step="1"
                          />
                          <span>{{ Math.round(draftFilters.locationRadius) }} {{ draftFilters.radiusUnit }}</span>
                        </div>
                        <div class="mode-row compact">
                          <button
                            type="button"
                            class="mode-button"
                            :class="{ active: draftFilters.radiusUnit === 'mi' }"
                            @click="setRadiusUnit('mi')"
                          >
                            Miles
                          </button>
                          <button
                            type="button"
                            class="mode-button"
                            :class="{ active: draftFilters.radiusUnit === 'km' }"
                            @click="setRadiusUnit('km')"
                          >
                            Kilometers
                          </button>
                        </div>
                    </div>

                    <div class="filter-group">
                        <label>Matched places</label>
                        <button type="button" class="secondary-action" @click="previewLocationSelection" :disabled="locationBusy">
                          {{ locationBusy ? 'Resolving area…' : 'Preview matched places' }}
                        </button>
                        <p v-if="locationPreviewSummary" class="hint-text">{{ locationPreviewSummary }}</p>
                        <button
                          v-if="hasMorePreviewCities"
                          type="button"
                          class="city-preview-more"
                          @click="openCityPreviewModal"
                        >
                          Show all matched places
                        </button>
                    </div>
                </div>

                <div class="filter-grid">
                    <div class="filter-group full-width">
                        <label for="job-company-input">Company filters</label>
                        <div class="custom-input-row">
                            <input
                                id="job-company-input"
                                name="job_company_input"
                                v-model.trim="companyInput"
                                type="text"
                                autocomplete="off"
                                autocapitalize="none"
                                autocorrect="off"
                                spellcheck="false"
                                placeholder="Add company and press Add"
                                @keyup.enter="addCustomFilterValue('companies')"
                            />
                            <button type="button" class="secondary-action" @click="addCustomFilterValue('companies')">Add</button>
                        </div>
                        <div class="chip-list" v-if="draftFilters.companies.length">
                            <button
                                class="chip"
                                type="button"
                                v-for="company in draftFilters.companies"
                                :key="company"
                                @click="removeFilterValue('companies', company)"
                                :title="`Remove ${company}`"
                            >
                                {{ company }} x
                            </button>
                        </div>
                    </div>
                </div>
            </section>
        </section>

        <JobBoardResultsSummary
          :loading="loading"
          :error="error"
          :jobs-length="jobs.length"
          :page="page"
          :total-jobs="totalJobs"
          :totals-are-estimated="totalsAreEstimated"
          :search-scope-summary="searchScopeSummary"
          :active-filter-chips="activeFilterChips"
          :compatibility-notice="compatibilityNotice"
          :location-limit-notice="locationLimitNotice"
          :can-widen-search="canWidenSearch"
          :sort-by="appliedFilters.sortBy"
          :sort-options="sortOptions"
          @clear="clearFilters"
          @remove-chip="removeActiveFilterChip"
          @sort-change="applySortChange"
          @widen="widenSearch"
        />

        <JobBoardDebugPanel
          v-if="showDebugTools"
          :diagnostics="lastSearchDiagnostics"
          :pretrim-location-notice="pretrimLocationNotice"
          :filter-metadata-version="filterMetadataVersion"
          :filter-metadata-hash="filterMetadataHash"
          :api-summary="lastApiSummary"
        />

        <JobBoardPagination
          v-if="!loading && !error"
          class="pagination pagination-top"
          id-prefix="jobs-top"
          :page="page"
          :total-pages="totalPages"
          :visible-pages="visiblePageButtons"
          :loading="loading"
          :has-next-page="hasNextPage"
          :totals-are-estimated="totalsAreEstimated"
          @previous="goToPreviousPage"
          @next="goToNextPage"
          @select-page="goToPage"
        />

        <div class="dashboard">
            <div class="empty-state" v-if="!loading && !error && !jobs.length">
                No jobs matched the selected filters.
                <div class="empty-state-actions">
                    <button type="button" @click="enableRemoteAndSearch" :disabled="loading || appliedFilters.includeRemote === true">Enable Remote</button>
                    <button type="button" @click="switchToCountryModeAndSearch" :disabled="loading || appliedFilters.locationMode === 'country'">Switch to Country</button>
                    <button type="button" @click="clearLocationAndSearch" :disabled="loading || !hasLocationFilterApplied">Clear Location</button>
                </div>
            </div>
            <JobPosting
                v-else
                v-for="job in jobs"
                :key="job.id"
                :job="job"
                :provider-attribution="providerAttributionByName[job.provider] || null"
                :show-debug-meta="showDebugTools"
            />
        </div>

        <JobBoardPagination
          v-if="!loading && !error"
          class="pagination pagination-bottom"
          id-prefix="jobs-bottom"
          :page="page"
          :total-pages="totalPages"
          :visible-pages="visiblePageButtons"
          :loading="loading"
          :has-next-page="hasNextPage"
          :totals-are-estimated="totalsAreEstimated"
          @previous="goToPreviousPage"
          @next="goToNextPage"
          @select-page="goToPage"
        />

        <div
          v-if="cityPreviewModalOpen"
          class="city-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="All area cities"
          @click="closeCityPreviewModal"
        >
          <div class="city-modal-dialog" v-draggable-modal="{ handle: '.city-modal-header' }" @click.stop>
            <div class="city-modal-header drag-handle">
              <h2>Matched Places</h2>
              <button type="button" class="city-modal-close" @click="closeCityPreviewModal">Close</button>
            </div>

            <p class="city-modal-subtitle">Showing all {{ locationPreviewNames.length }} matched places.</p>

            <div class="city-modal-scroll">
              <div class="city-sort-row">
                <button
                  type="button"
                  class="city-sort-btn"
                  :class="{ active: citySortMode === 'closest' }"
                  @click="setCitySortMode('closest')"
                >
                  Closest
                </button>
                <button
                  type="button"
                  class="city-sort-btn"
                  :class="{ active: citySortMode === 'alpha' }"
                  @click="setCitySortMode('alpha')"
                >
                  A to Z
                </button>
                <button
                  type="button"
                  class="city-sort-btn"
                  :class="{ active: citySortMode === 'reverse' }"
                  @click="setCitySortMode('reverse')"
                >
                  Z to A
                </button>
              </div>
              <p class="warn-text" v-if="closestSortNotice">{{ closestSortNotice }}</p>
              <ul class="city-modal-list">
                <li v-for="city in sortedLocationPreviewCities" :key="city.sort_key">
                  {{ city.name }}
                  <span v-if="city.distance_miles !== null" class="city-distance">({{ city.distance_miles.toFixed(1) }} mi)</span>
                </li>
              </ul>
            </div>

            <div class="city-modal-actions">
              <button type="button" @click="closeCityPreviewModal">Close</button>
            </div>
          </div>
        </div>
    </div>
</template>


<script>
import JobPosting from "../components/JobPosting.vue";
import JobBoardPrimaryFilters from "../components/job-board/JobBoardPrimaryFilters.vue";
import JobBoardResultsSummary from "../components/job-board/JobBoardResultsSummary.vue";
import JobBoardDebugPanel from "../components/job-board/JobBoardDebugPanel.vue";
import JobBoardPagination from "../components/job-board/JobBoardPagination.vue";
import {
  getCachedLocation,
  requestBrowserLocation,
  setCachedLocation
} from "../lib/geolocation";
import { publishCurrentPageDiagnostics, clearCurrentPageDiagnostics } from "../lib/debugDiagnostics";
import { subscribeDebugTools } from "../lib/debugTools";

const ALL_COUNTRIES_CODE = "ALL"
const DEFAULT_COUNTRY_OPTION = Object.freeze({
  code: ALL_COUNTRIES_CODE,
  name: "All Countries",
  observed_count: 0,
})
const DEFAULT_SORT_BY = "date_desc"
const POSTED_DATE_PRESETS = new Set(["any", "today", "3", "7", "30", "custom"])
const JOB_SORT_OPTIONS = [
  { value: "date_desc", label: "Most Recent" },
  { value: "quality_desc", label: "Best Match" },
  { value: "date_asc", label: "Oldest First" },
]
const LEVEL_VALUE_ALIASES = {
  internship: "internship",
  entry: "entry",
  "entry level": "entry",
  mid: "mid",
  "mid level": "mid",
  senior: "senior",
  "senior level": "senior",
  manager: "manager",
  management: "manager",
  director: "director",
  vp: "vp",
}
const LEVEL_LABELS = {
  internship: "Internship",
  entry: "Entry",
  mid: "Mid",
  senior: "Senior",
  manager: "Manager",
  director: "Director",
  vp: "VP",
}
const DEFAULT_LEVEL_OPTIONS = Object.entries(LEVEL_LABELS).map(([value, label]) => ({
  value,
  label,
  observedCount: 0,
}))

function normalizeRouteQueryScalar(value) {
  if (Array.isArray(value)) {
    return normalizeRouteQueryScalar(value[0])
  }
  return typeof value === "string" ? value.trim() : ""
}

function normalizeRouteQueryList(value) {
  if (Array.isArray(value)) {
    return value.map(item => normalizeRouteQueryScalar(item)).filter(Boolean)
  }
  const normalized = normalizeRouteQueryScalar(value)
  return normalized ? [normalized] : []
}

function stringifyRouteQuery(query = {}) {
  const params = new URLSearchParams()
  for (const key of Object.keys(query || {}).sort()) {
    const rawValue = query[key]
    if (Array.isArray(rawValue)) {
      for (const item of rawValue) {
        const normalized = normalizeRouteQueryScalar(item)
        if (normalized) {
          params.append(key, normalized)
        }
      }
      continue
    }

    const normalized = normalizeRouteQueryScalar(rawValue)
    if (normalized) {
      params.append(key, normalized)
    }
  }
  return params.toString()
}

function normalizeCountryCode(value) {
  return String(value || "").trim().toUpperCase()
}

function isAllCountriesCode(value) {
  return normalizeCountryCode(value) === ALL_COUNTRIES_CODE
}

function buildCountryOptions(values = []) {
  const options = []
  const seen = new Set([ALL_COUNTRIES_CODE])

  for (const rawCountry of values || []) {
    const code = normalizeCountryCode(rawCountry?.code)
    const name = String(rawCountry?.name || rawCountry?.code || "").trim()
    if (!code || !name || seen.has(code)) continue
    seen.add(code)
    options.push({
      code,
      name,
      observed_count: Number(rawCountry?.observed_count || 0),
    })
  }

  return [DEFAULT_COUNTRY_OPTION, ...options]
}

export default {
  name: "JobBoard",
  components: {
    JobPosting,
    JobBoardPrimaryFilters,
    JobBoardResultsSummary,
    JobBoardDebugPanel,
    JobBoardPagination,
  },
  data() {
    const locationSourceMode = "muse"
    const uiPageSize = 10
    const maxLocationParams = 60

    const categoryGroups = [
      {
        name: "Tech",
        muse_categories: [
          "Software Engineer",
          "Software Engineering",
          "Computer and IT",
          "IT",
          "Data and Analytics",
          "Data Science",
          "Design and UX",
          "UX",
          "Science and Engineering"
        ]
      },
      {
        name: "Finance",
        muse_categories: ["Accounting", "Accounting and Finance", "Finance", "Real Estate"]
      },
      {
        name: "Product",
        muse_categories: ["Product", "Product Management", "Project Management"]
      },
      {
        name: "People",
        muse_categories: ["HR", "Human Resources and Recruitment", "Recruiting", "Social Services"]
      },
      {
        name: "Business and Operations",
        muse_categories: ["Business Operations", "Corporate", "Operations", "Office Administration", "Administration and Office"]
      },
      {
        name: "Sales and Marketing",
        muse_categories: [
          "Sales",
          "Marketing",
          "Advertising and Marketing",
          "Public Relations",
          "Media, PR, and Communications",
          "Account Management",
          "Account Management/Customer Success"
        ]
      },
      {
        name: "Customer and Support",
        muse_categories: ["Customer Service", "Education", "Legal Services"]
      }
    ]

    const categoryOptions = Array.from(new Set(
      categoryGroups.flatMap(group => group.muse_categories || [])
    ))

    const categoryAliases = {
      tech: "Tech",
      technology: "Tech",
      engineering: "Tech",
      fintech: "Finance",
      finance: "Finance",
      product: "Product",
      people: "People",
      hr: "People",
      operations: "Business and Operations",
      business: "Business and Operations",
      sales: "Sales and Marketing",
      marketing: "Sales and Marketing",
      support: "Customer and Support"
    }

    const categoryLookup = {}
    for (const value of categoryOptions) {
      categoryLookup[value.toLowerCase()] = value
    }
    for (const group of categoryGroups) {
      categoryLookup[group.name.toLowerCase()] = group.name
    }
    for (const [alias, canonical] of Object.entries(categoryAliases)) {
      categoryLookup[alias] = canonical
    }

    const levelOptions = DEFAULT_LEVEL_OPTIONS.map(option => ({ ...option }))

    const levelLookup = {}
    for (const value of levelOptions) {
      levelLookup[value.value.toLowerCase()] = value.value
      levelLookup[value.label.toLowerCase()] = value.value
    }

    const levelLabelLookup = {}
    for (const option of levelOptions) {
      levelLabelLookup[option.value] = option.label
    }

    const categoryMapLookup = {}
    for (const group of categoryGroups) {
      categoryMapLookup[group.name] = group
    }

    const countryOptions = buildCountryOptions()
    const providerOptions = []

    const defaultFilters = {
      categories: [],
      levels: [],
      includeHybrid: true,
      includeRemote: true,
      locationMode: "country",
      locationRadius: 25,
      radiusUnit: "mi",
      manualLocationQuery: "",
      countryCode: ALL_COUNTRIES_CODE,
      locationNames: [],
      companies: [],
      provider: "",
      keyword: "",
      sortBy: DEFAULT_SORT_BY,
      datePreset: "any",
      customAfterDate: ""
    }

    return {
      jobs: [],
      providerAttributionByName: {},
      loading: false,
      error: "",
      page: 1,
      pageSize: uiPageSize,
      totalJobs: 0,
      totalPages: 1,
      totalsAreEstimated: false,
      hasNextPage: false,
      locationLimitNotice: "",
      pretrimLocationNotice: "",
      filterMetadataVersion: "",
      filterMetadataHash: "",
      lastSearchDiagnostics: {},
      lastApiSummary: {},
      maxLocationParams,
      locationSourceMode,
      categoryGroups,
      categoryMapLookup,
      categoryOptions,
      categoryLookup,
      levelOptions,
      levelLookup,
      levelLabelLookup,
      countryOptions,
      providerOptions,
      sortOptions: JOB_SORT_OPTIONS.map(option => ({ ...option })),
      categoryInput: "",
      categoryInfo: "",
      categoryMenuOpen: false,
      categoryActiveIndex: 0,
      advancedFiltersOpen: false,
      levelInput: "",
      levelInfo: "",
      levelMenuOpen: false,
      levelActiveIndex: 0,
      advancedLocationModalOpen: false,
      cityPreviewVisibleLimit: 10,
      cityPreviewModalOpen: false,
      citySortMode: "closest",
      companyInput: "",
      locationFallbackInput: "",
      locationBusy: false,
      locationInfo: "",
      locationError: "",
      locationWarning: "",
      locationPreviewNames: [],
      locationPreviewCities: [],
      locationPreviewCandidates: [],
      locationPreviewCenter: null,
      resolvedLocation: null,
      showDebugTools: false,
      debugToolsUnsubscribe: null,
      routeHydrationReady: false,
      draftFilters: JSON.parse(JSON.stringify(defaultFilters)),
      appliedFilters: JSON.parse(JSON.stringify(defaultFilters))
    };
  },
  computed: {
    maxRadiusForUnit() {
      return this.draftFilters.radiusUnit === "km" ? 161 : 100
    },
    filteredCategoryOptions() {
      const selected = new Set((this.draftFilters.categories || []).map(value => value.toLowerCase()))
      const query = (this.categoryInput || "").trim().toLowerCase()

      const options = this.categoryOptions.filter(option => {
        if (selected.has(option.toLowerCase())) return false
        if (!query) return true
        return option.toLowerCase().includes(query)
      })

      return options.slice(0, 12)
    },
    showCategoryMenu() {
      return this.categoryMenuOpen && this.filteredCategoryOptions.length > 0
    },
    selectedCategoryGroups() {
      return (this.draftFilters.categories || [])
        .map(name => this.categoryMapLookup[name])
        .filter(Boolean)
    },
    selectedCustomCategories() {
      return (this.draftFilters.categories || []).filter(name => !this.categoryMapLookup[name])
    },
    filteredLevelOptions() {
      const selected = new Set((this.draftFilters.levels || []).map(value => value.toLowerCase()))
      const query = (this.levelInput || "").trim().toLowerCase()

      const options = this.levelOptions.filter(option => {
        if (selected.has(option.value.toLowerCase())) return false
        if (!query) return true
        return option.label.toLowerCase().includes(query) || option.value.toLowerCase().includes(query)
      })

      return options.slice(0, 8)
    },
    showLevelMenu() {
      return this.levelMenuOpen && this.filteredLevelOptions.length > 0
    },
    visibleLocationPreviewNames() {
      return (this.locationPreviewNames || []).slice(0, this.cityPreviewVisibleLimit)
    },
    selectedCountryName() {
      return this.getCountryName(this.draftFilters.countryCode)
    },
    heroSearchCopy() {
      if (this.isAllCountriesCode(this.draftFilters.countryCode)) {
        return "Default results search across all countries with remote and hybrid roles included."
      }
      return `Default results search across ${this.selectedCountryName} with remote and hybrid roles included.`
    },
    locationPreviewSummary() {
      if (this.draftFilters.locationMode === "country" && this.isAllCountriesCode(this.draftFilters.countryCode)) {
        return "All Countries stays broad, so matched-place previews are disabled for this mode."
      }
      if (!this.locationPreviewNames.length) return ""
      if (this.draftFilters.locationMode === "country") {
        return `Previewing ${this.locationPreviewNames.length} matched places in ${this.getCountryName(this.draftFilters.countryCode)}.`
      }
      const centerName = this.resolvedLocation?.city || this.draftFilters.manualLocationQuery || "your selected area"
      return `Previewing ${this.locationPreviewNames.length} matched places around ${centerName}.`
    },
    hiddenLocationPreviewCount() {
      const hidden = (this.locationPreviewNames || []).length - this.cityPreviewVisibleLimit
      return hidden > 0 ? hidden : 0
    },
    hasMorePreviewCities() {
      return this.hiddenLocationPreviewCount > 0
    },
    sortedLocationPreviewCities() {
      const rawCities = this.locationPreviewCities.length
        ? this.locationPreviewCities
        : this.locationPreviewNames.map(name => ({ name }))

      const withDistance = rawCities.map((city, index) => {
        const name = (city.name || "").trim()
        let distance = typeof city.distance_miles === "number" ? city.distance_miles : null

        if (
          distance === null
          && this.locationPreviewCenter
          && typeof city.latitude === "number"
          && typeof city.longitude === "number"
        ) {
          distance = this.haversineMiles(
            this.locationPreviewCenter.latitude,
            this.locationPreviewCenter.longitude,
            city.latitude,
            city.longitude
          )
        }

        return {
          name,
          distance_miles: distance,
          sort_key: `${name}-${index}`
        }
      }).filter(city => city.name)

      const sorted = [...withDistance]
      if (this.citySortMode === "alpha") {
        sorted.sort((a, b) => a.name.localeCompare(b.name))
      } else if (this.citySortMode === "reverse") {
        sorted.sort((a, b) => b.name.localeCompare(a.name))
      } else {
        const hasAnyDistance = sorted.some(city => city.distance_miles !== null)
        if (!hasAnyDistance) {
          sorted.sort((a, b) => a.name.localeCompare(b.name))
        } else {
          sorted.sort((a, b) => {
            const aDist = a.distance_miles === null ? Number.MAX_SAFE_INTEGER : a.distance_miles
            const bDist = b.distance_miles === null ? Number.MAX_SAFE_INTEGER : b.distance_miles
            if (aDist !== bDist) return aDist - bDist
            return a.name.localeCompare(b.name)
          })
        }
      }

      return sorted
    },
    closestSortNotice() {
      if (this.citySortMode !== "closest") return ""
      const hasAnyDistance = this.sortedLocationPreviewCities.some(city => city.distance_miles !== null)
      if (hasAnyDistance) return ""
      return "Closest sorting needs a known center location, so this list is currently alphabetical."
    },
    visiblePageButtons() {
      const total = Math.max(1, Number(this.totalPages || 1))
      const current = Math.max(1, Number(this.page || 1))
      const span = 2
      const start = Math.max(1, current - span)
      const end = Math.min(total, current + span)

      const pages = []
      for (let p = start; p <= end; p += 1) {
        pages.push(p)
      }
      return pages
    },
    compatibilityNotice() {
      const overlapCount = Number(this.lastSearchDiagnostics.acceptedByConstraintOverlap || 0)
      if (!overlapCount) return ""
      if (this.appliedFilters.includeRemote === true) return ""
      const policy = (this.lastSearchDiagnostics.constraintPolicyRemoteOff || "").trim()
      const policyHint = policy ? ` Policy: ${policy}.` : ""
      return `${overlapCount} remote role(s) remained because location constraints overlapped your selected area.${policyHint}`
    },
    hasLocationFilterApplied() {
      const names = Array.isArray(this.appliedFilters.locationNames) ? this.appliedFilters.locationNames : []
      if (names.length > 0) return true
      return this.appliedFilters.locationMode === "manual" || this.appliedFilters.locationMode === "nearby"
    },
    activeFilterChips() {
      const chips = []
      const filters = this.appliedFilters || {}

      for (const category of filters.categories || []) {
        chips.push({ key: `category-${category}`, type: "category", value: category, label: `Category: ${category}` })
      }
      for (const level of filters.levels || []) {
        chips.push({ key: `level-${level}`, type: "level", value: level, label: `Level: ${this.formatLevelLabel(level)}` })
      }
      for (const company of filters.companies || []) {
        chips.push({ key: `company-${company}`, type: "company", value: company, label: `Company: ${company}` })
      }
      if (this.normalizeProviderValue(filters.provider)) {
        chips.push({
          key: "provider",
          type: "provider",
          value: this.normalizeProviderValue(filters.provider),
          label: `Source: ${this.getProviderLabel(filters.provider)}`,
        })
      }

      const keyword = String(filters.keyword || "").trim()
      if (keyword) {
        chips.push({ key: "keyword", type: "keyword", value: "", label: `Keyword: ${keyword}` })
      }

      const datePreset = String(filters.datePreset || "any").trim().toLowerCase()
      if (datePreset !== "any") {
        const label = this.buildPostedPresetChipLabel(filters)
        chips.push({ key: "date", type: "date", value: "", label })
      }

      if (filters.includeRemote === false) {
        chips.push({ key: "remote-off", type: "remote", value: "", label: "Remote off" })
      }
      if (filters.includeHybrid === false) {
        chips.push({ key: "hybrid-off", type: "hybrid", value: "", label: "Hybrid off" })
      }

      if ((filters.locationNames || []).length > 0) {
        chips.push({
          key: "location-names",
          type: "location",
          value: "",
          label: this.buildLocationChipLabel(filters),
        })
      }

      const normalizedCountryCode = (filters.countryCode || "").trim().toUpperCase()
      const normalizedLocationMode = (filters.locationMode || "country").trim().toLowerCase()
      if (normalizedCountryCode && !this.isAllCountriesCode(normalizedCountryCode)) {
        chips.push({
          key: "country",
          type: "country",
          value: "",
          label: normalizedLocationMode === "country"
            ? `Country: ${this.getCountryName(filters.countryCode)}`
            : `Country boundary: ${this.getCountryName(filters.countryCode)}`,
        })
      }

      return chips
    },
    canWidenSearch() {
      const filters = this.appliedFilters || {}
      const hasCountryMode = (filters.locationMode || "").trim().toLowerCase() === "country"
      const hasBroadWorkSetup = filters.includeRemote === true && filters.includeHybrid === true
      const hasAllCountriesScope = this.isAllCountriesCode(filters.countryCode)
      return !(hasCountryMode && hasBroadWorkSetup && hasAllCountriesScope)
    },
    searchScopeSummary() {
      const filters = this.appliedFilters || {}
      const workSetup = this.buildWorkSetupSummary(filters)
      const providerSummary = this.normalizeProviderValue(filters.provider)
        ? ` from ${this.getProviderLabel(filters.provider)}`
        : ""

      if ((filters.locationMode || "").trim().toLowerCase() === "country") {
        if (this.isAllCountriesCode(filters.countryCode)) {
          return `Searching across all countries${providerSummary} with ${workSetup}.`
        }
        return `Searching across ${this.getCountryName(filters.countryCode)}${providerSummary} with ${workSetup}.`
      }

      const selectedCount = (filters.locationNames || []).length
      if (selectedCount > 0) {
        const centerName = this.resolvedLocation?.city || filters.manualLocationQuery || "your selected area"
        return `Searching around ${centerName}${providerSummary} across ${selectedCount} matched locations with ${workSetup}.`
      }

      return `Searching${providerSummary} with ${workSetup}.`
    }
  },
  watch: {
    async "$route.query"(nextQuery) {
      if (!this.routeHydrationReady) return
      const routeSignature = stringifyRouteQuery(nextQuery || {})
      const stateSignature = stringifyRouteQuery(this.buildRouteQueryObject())
      if (routeSignature === stateSignature) return
      await this.hydrateFromRouteQuery(nextQuery, "route-query")
    },
  },
  methods: {
    createDefaultFilters() {
      return {
        categories: [],
        levels: [],
        includeHybrid: true,
        includeRemote: true,
        locationMode: "country",
        locationRadius: 25,
        radiusUnit: "mi",
        manualLocationQuery: "",
        countryCode: ALL_COUNTRIES_CODE,
        locationNames: [],
        companies: [],
        provider: "",
        keyword: "",
        sortBy: DEFAULT_SORT_BY,
        datePreset: "any",
        customAfterDate: ""
      }
    },
    cloneFilters(filters) {
      return JSON.parse(JSON.stringify(filters))
    },
    normalizeCountryCode(value) {
      return normalizeCountryCode(value)
    },
    isAllCountriesCode(value) {
      return isAllCountriesCode(value)
    },
    countryCodeForRoute(value) {
      return this.normalizeCountryCode(value) || ALL_COUNTRIES_CODE
    },
    countryCodeForApi(value) {
      const normalized = this.normalizeCountryCode(value)
      return this.isAllCountriesCode(normalized) ? "" : normalized
    },
    withOptionalCountryCode(path, countryCode, extraParams = {}) {
      const params = new URLSearchParams()
      for (const [key, rawValue] of Object.entries(extraParams || {})) {
        if (rawValue === undefined || rawValue === null) continue
        params.set(key, String(rawValue))
      }

      const apiCountryCode = this.countryCodeForApi(countryCode)
      if (apiCountryCode) {
        params.set("country_code", apiCountryCode)
      }

      const query = params.toString()
      return query ? `${path}?${query}` : path
    },
    normalizeSortBy(value) {
      const normalized = String(value || "").trim().toLowerCase()
      return this.sortOptions.some(option => option.value === normalized) ? normalized : DEFAULT_SORT_BY
    },
    normalizeProviderValue(value) {
      const normalized = String(value || "").trim().toLowerCase()
      if (!normalized || normalized === "all") return ""
      return normalized
    },
    getProviderLabel(value) {
      const normalized = this.normalizeProviderValue(value)
      if (!normalized) return "All providers"
      const optionMatch = (this.providerOptions || []).find(option => option.value === normalized)
      if (optionMatch?.label) return optionMatch.label
      const attributionLabel = (this.providerAttributionByName?.[normalized] || {}).label
      return attributionLabel || normalized
    },
    formatLevelLabel(value) {
      const clean = (value || "").trim()
      if (!clean) return ""
      return this.levelLabelLookup[clean] || this.levelLabelLookup[clean.toLowerCase()] || clean
    },
    buildPostedPresetChipLabel(filters = {}) {
      const preset = String(filters.datePreset || "any").trim().toLowerCase()
      if (preset === "custom") {
        return `Posted after: ${filters.customAfterDate || "custom date"}`
      }
      if (preset === "today") return "Posted: today"
      if (preset === "3") return "Posted: past 3 days"
      if (preset === "7") return "Posted: past week"
      if (preset === "30") return "Posted: past month"
      return ""
    },
    buildLocationChipLabel(filters = {}) {
      const locationMode = (filters.locationMode || "country").trim().toLowerCase()
      const selectedCount = Array.isArray(filters.locationNames) ? filters.locationNames.length : 0
      if (locationMode === "nearby") {
        return selectedCount
          ? `Nearby (${selectedCount} matched places)`
          : "Nearby search"
      }
      if (locationMode === "manual") {
        const query = (filters.manualLocationQuery || "").trim()
        if (selectedCount && query) {
          return `Custom area: ${query} (${selectedCount} matched places)`
        }
        return query ? `Custom area: ${query}` : "Custom area"
      }
      return selectedCount ? `Matched places (${selectedCount})` : "Location filter"
    },
    parseBooleanRouteValue(value, fallback = false) {
      const normalized = normalizeRouteQueryScalar(value).toLowerCase()
      if (!normalized) return fallback
      if (["1", "true", "yes", "on"].includes(normalized)) return true
      if (["0", "false", "no", "off"].includes(normalized)) return false
      return fallback
    },
    parsePositiveInteger(value, fallback, minimum = 1, maximum = Number.MAX_SAFE_INTEGER) {
      const numeric = Number.parseInt(normalizeRouteQueryScalar(value), 10)
      if (!Number.isFinite(numeric)) return fallback
      return Math.max(minimum, Math.min(maximum, numeric))
    },
    buildRouteQueryObject() {
      const filters = this.appliedFilters || this.createDefaultFilters()
      const query = {
        country_code: this.countryCodeForRoute(filters.countryCode),
        location_mode: (filters.locationMode || "country").trim().toLowerCase() || "country",
        include_remote: filters.includeRemote === false ? "false" : "true",
        include_hybrid: filters.includeHybrid === false ? "false" : "true",
        sort_by: this.normalizeSortBy(filters.sortBy),
      }

      const keyword = (filters.keyword || "").trim()
      if (keyword) {
        query.q = keyword
      }

      const categories = this.normalizeUnique(filters.categories)
      if (categories.length) {
        query.category = categories
      }

      const levels = this.normalizeUnique(filters.levels)
      if (levels.length) {
        query.level = levels
      }

      const companies = this.normalizeUnique(filters.companies)
      if (companies.length) {
        query.company = companies
      }

      const provider = this.normalizeProviderValue(filters.provider)
      if (provider) {
        query.provider = provider
      }

      const postedPreset = String(filters.datePreset || "any").trim().toLowerCase()
      if (postedPreset !== "any") {
        query.posted = POSTED_DATE_PRESETS.has(postedPreset) ? postedPreset : "any"
      }
      if (postedPreset === "custom" && /^\d{4}-\d{2}-\d{2}$/.test((filters.customAfterDate || "").trim())) {
        query.after = (filters.customAfterDate || "").trim()
      }

      if (query.location_mode !== "country") {
        const locationQuery = (filters.manualLocationQuery || "").trim()
        if (locationQuery) {
          query.location_query = locationQuery
        }
        query.radius = String(Math.max(1, Math.round(Number(filters.locationRadius || 25))))
        query.radius_unit = filters.radiusUnit === "km" ? "km" : "mi"

        if (query.location_mode === "nearby") {
          const center = this.getBestKnownCenter()
          if (center && Number.isFinite(Number(center.latitude)) && Number.isFinite(Number(center.longitude))) {
            query.center_lat = Number(center.latitude).toFixed(2)
            query.center_lng = Number(center.longitude).toFixed(2)
          }
        }
      }

      if (this.page > 1) {
        query.page = String(this.page)
      }

      return query
    },
    async syncRouteQuery() {
      const nextQuery = this.buildRouteQueryObject()
      const nextSignature = stringifyRouteQuery(nextQuery)
      const currentSignature = stringifyRouteQuery(this.$route?.query || {})
      if (nextSignature === currentSignature) return

      this.routeHydrationReady = false
      try {
        await this.$router.replace({ path: this.$route.path, query: nextQuery })
      } finally {
        this.routeHydrationReady = true
      }
    },
    parseRouteQueryFilters(query = {}) {
      const filters = this.createDefaultFilters()
      filters.keyword = normalizeRouteQueryScalar(query.q)
      filters.categories = this.normalizeCategoryValues(normalizeRouteQueryList(query.category))
      filters.levels = this.normalizeLevelValues(normalizeRouteQueryList(query.level))
      filters.companies = this.normalizeUnique(normalizeRouteQueryList(query.company))
      filters.provider = this.normalizeProviderValue(normalizeRouteQueryScalar(query.provider))
      filters.sortBy = this.normalizeSortBy(normalizeRouteQueryScalar(query.sort_by))

      const postedPreset = normalizeRouteQueryScalar(query.posted).toLowerCase()
      const customAfterDate = normalizeRouteQueryScalar(query.after)
      if (POSTED_DATE_PRESETS.has(postedPreset) && postedPreset !== "any") {
        filters.datePreset = postedPreset
      } else if (/^\d{4}-\d{2}-\d{2}$/.test(customAfterDate)) {
        filters.datePreset = "custom"
      }
      filters.customAfterDate = /^\d{4}-\d{2}-\d{2}$/.test(customAfterDate) ? customAfterDate : ""
      if (filters.datePreset === "custom" && !filters.customAfterDate) {
        filters.datePreset = "any"
      }

      const countryCode = normalizeRouteQueryScalar(query.country_code).toUpperCase()
      const availableCountryCodes = new Set((this.countryOptions || []).map(country => String(country?.code || "").trim().toUpperCase()).filter(Boolean))
      filters.countryCode = availableCountryCodes.has(countryCode)
        ? countryCode
        : (this.countryOptions[0]?.code || ALL_COUNTRIES_CODE)

      const locationMode = normalizeRouteQueryScalar(query.location_mode).toLowerCase()
      filters.locationMode = ["country", "nearby", "manual"].includes(locationMode) ? locationMode : "country"
      filters.manualLocationQuery = normalizeRouteQueryScalar(query.location_query)
      filters.radiusUnit = normalizeRouteQueryScalar(query.radius_unit).toLowerCase() === "km" ? "km" : "mi"
      filters.locationRadius = this.parsePositiveInteger(
        query.radius,
        filters.radiusUnit === "km" ? 40 : 25,
        1,
        filters.radiusUnit === "km" ? 161 : 100,
      )
      filters.includeRemote = this.parseBooleanRouteValue(query.include_remote, true)
      filters.includeHybrid = this.parseBooleanRouteValue(query.include_hybrid, true)
      filters.locationNames = []

      if (
        this.providerOptions.length
        && this.normalizeProviderValue(filters.provider)
        && !this.providerOptions.some(option => option.value === this.normalizeProviderValue(filters.provider))
      ) {
        filters.provider = ""
      }

      const page = this.parsePositiveInteger(query.page, 1, 1, Number.MAX_SAFE_INTEGER)
      return { filters, page }
    },
    async restoreResolvedLocationFromRoute(filters, routeQuery = {}) {
      this.resolvedLocation = null

      const locationMode = (filters?.locationMode || "country").trim().toLowerCase()
      if (locationMode === "country") return

      const lat = Number(normalizeRouteQueryScalar(routeQuery.center_lat))
      const lng = Number(normalizeRouteQueryScalar(routeQuery.center_lng))
      if (locationMode === "nearby" && Number.isFinite(lat) && Number.isFinite(lng)) {
        this.resolvedLocation = {
          latitude: lat,
          longitude: lng,
          city: (filters?.manualLocationQuery || "").trim(),
          display_name: (filters?.manualLocationQuery || "").trim(),
          country_code: this.countryCodeForApi(filters?.countryCode),
          source: "route",
        }
        setCachedLocation(this.resolvedLocation)
        return
      }

      const locationQuery = (filters?.manualLocationQuery || "").trim()
      if (locationQuery) {
        try {
          const payload = await this.fetchJson(this.withOptionalCountryCode("/api/geolocation/geocode", filters?.countryCode, {
            q: locationQuery,
          }))
          this.resolvedLocation = payload
          setCachedLocation(payload)
          return
        } catch (error) {
          console.error("Route geocode failed", error)
        }
      }

      const cached = getCachedLocation()
      if (cached?.latitude && cached?.longitude) {
        this.resolvedLocation = cached
      }
    },
    async hydrateFromRouteQuery(query = {}, reason = "route-hydrated") {
      this.routeHydrationReady = false
      this.locationError = ""
      this.locationWarning = ""
      this.locationInfo = ""
      this.locationLimitNotice = ""
      this.pretrimLocationNotice = ""
      this.categoryInput = ""
      this.categoryInfo = ""
      this.categoryActiveIndex = 0
      this.categoryMenuOpen = false
      this.levelInput = ""
      this.levelInfo = ""
      this.levelActiveIndex = 0
      this.levelMenuOpen = false
      this.companyInput = ""
      this.cityPreviewModalOpen = false

      try {
        const { filters, page } = this.parseRouteQueryFilters(query)
        this.draftFilters = this.cloneFilters(filters)
        this.appliedFilters = this.cloneFilters(filters)
        this.page = page
        this.locationPreviewNames = []
        this.locationPreviewCities = []
        this.locationPreviewCandidates = []
        this.locationPreviewCenter = null

        await this.restoreResolvedLocationFromRoute(this.draftFilters, query)

        const useResolvedLocationList = this.draftFilters.locationMode !== "country"
        const locationNames = useResolvedLocationList ? await this.resolveLocationNamesFromDraft() : []
        const preflightSelection = this.buildPreflightLocationSelection(locationNames, this.draftFilters.locationMode)
        this.pretrimLocationNotice = preflightSelection.requestedCount
          ? `Using ${preflightSelection.usedCount} of ${preflightSelection.requestedCount} resolved locations (${preflightSelection.strategy}).`
          : ""

        this.draftFilters.categories = this.normalizeCategoryValues(this.draftFilters.categories)
        this.draftFilters.levels = this.normalizeLevelValues(this.draftFilters.levels)
        this.draftFilters.companies = this.normalizeUnique(this.draftFilters.companies)
        this.draftFilters.provider = this.normalizeProviderValue(this.draftFilters.provider)
        this.draftFilters.sortBy = this.normalizeSortBy(this.draftFilters.sortBy)
        this.draftFilters.locationNames = preflightSelection.selected
        this.appliedFilters = this.cloneFilters(this.draftFilters)

        await this.loadJobs()
        this.publishDebugState(reason)
      } finally {
        this.routeHydrationReady = true
      }
    },
    async applySortChange(nextSortBy) {
      const normalizedSort = this.normalizeSortBy(nextSortBy)
      if (normalizedSort === this.normalizeSortBy(this.appliedFilters.sortBy)) {
        return
      }
      this.draftFilters.sortBy = normalizedSort
      this.appliedFilters.sortBy = normalizedSort
      this.page = 1
      await this.loadJobs()
      this.publishDebugState("sort-changed")
    },
    getCountryName(code) {
      const normalized = this.normalizeCountryCode(code)
      const match = (this.countryOptions || []).find(country => country.code === normalized)
      return match?.name || (this.isAllCountriesCode(normalized) ? DEFAULT_COUNTRY_OPTION.name : normalized) || DEFAULT_COUNTRY_OPTION.name
    },
    buildWorkSetupSummary(filters = {}) {
      const includeRemote = filters.includeRemote !== false
      const includeHybrid = filters.includeHybrid !== false

      if (includeRemote && includeHybrid) return "remote and hybrid roles included"
      if (includeRemote) return "remote roles included"
      if (includeHybrid) return "hybrid roles included"
      return "on-site focused results"
    },
    async removeActiveFilterChip(chip) {
      if (!chip || !chip.type) return

      const removeValue = (list, value) => (list || []).filter(item => item !== value)

      if (chip.type === "category") {
        this.draftFilters.categories = removeValue(this.draftFilters.categories, chip.value)
        this.appliedFilters.categories = removeValue(this.appliedFilters.categories, chip.value)
      } else if (chip.type === "level") {
        this.draftFilters.levels = removeValue(this.draftFilters.levels, chip.value)
        this.appliedFilters.levels = removeValue(this.appliedFilters.levels, chip.value)
      } else if (chip.type === "company") {
        this.draftFilters.companies = removeValue(this.draftFilters.companies, chip.value)
        this.appliedFilters.companies = removeValue(this.appliedFilters.companies, chip.value)
      } else if (chip.type === "provider") {
        this.draftFilters.provider = ""
        this.appliedFilters.provider = ""
      } else if (chip.type === "keyword") {
        this.draftFilters.keyword = ""
        this.appliedFilters.keyword = ""
      } else if (chip.type === "date") {
        this.draftFilters.datePreset = "any"
        this.appliedFilters.datePreset = "any"
        this.draftFilters.customAfterDate = ""
        this.appliedFilters.customAfterDate = ""
      } else if (chip.type === "remote") {
        this.draftFilters.includeRemote = true
        this.appliedFilters.includeRemote = true
      } else if (chip.type === "hybrid") {
        this.draftFilters.includeHybrid = true
        this.appliedFilters.includeHybrid = true
      } else if (chip.type === "location") {
        await this.clearLocationAndSearch()
        return
      } else if (chip.type === "country") {
        this.draftFilters.countryCode = ALL_COUNTRIES_CODE
        this.appliedFilters.countryCode = ALL_COUNTRIES_CODE
        this.page = 1
        if ((this.appliedFilters.locationMode || "").trim().toLowerCase() === "country") {
          await this.loadJobs()
        } else {
          await this.applyFilters()
        }
        return
      }

      this.page = 1
      await this.loadJobs()
      this.publishDebugState("active-filter-chip-removed")
    },
    async widenSearch() {
      this.draftFilters.includeRemote = true
      this.appliedFilters.includeRemote = true
      this.draftFilters.includeHybrid = true
      this.appliedFilters.includeHybrid = true
      this.draftFilters.locationMode = "country"
      this.appliedFilters.locationMode = "country"
      this.draftFilters.countryCode = ALL_COUNTRIES_CODE
      this.appliedFilters.countryCode = ALL_COUNTRIES_CODE
      this.draftFilters.locationNames = []
      this.appliedFilters.locationNames = []
      this.locationPreviewNames = []
      this.locationPreviewCities = []
      this.locationPreviewCandidates = []
      this.locationPreviewCenter = null
      this.page = 1
      await this.applyFilters()
      this.publishDebugState("widen-search")
    },
    async enableRemoteAndSearch() {
      this.draftFilters.includeRemote = true
      this.appliedFilters.includeRemote = true
      this.page = 1
      await this.loadJobs()
      this.publishDebugState("enable-remote")
    },
    async switchToCountryModeAndSearch() {
      this.draftFilters.locationMode = "country"
      this.appliedFilters.locationMode = "country"
      this.page = 1
      await this.applyFilters()
      this.publishDebugState("switch-country-mode")
    },
    async clearLocationAndSearch() {
      this.resolvedLocation = null
      this.locationFallbackInput = ""
      this.draftFilters.manualLocationQuery = ""
      this.appliedFilters.manualLocationQuery = ""
      this.draftFilters.locationNames = []
      this.appliedFilters.locationNames = []
      this.draftFilters.locationMode = "country"
      this.appliedFilters.locationMode = "country"
      this.locationPreviewNames = []
      this.locationPreviewCities = []
      this.locationPreviewCandidates = []
      this.locationPreviewCenter = null
      this.page = 1
      await this.applyFilters()
      this.publishDebugState("clear-location")
    },
    normalizeUnique(values) {
      const out = []
      const seen = new Set()
      for (const value of values || []) {
        const clean = (value || "").trim()
        if (!clean) continue
        const key = clean.toLowerCase()
        if (seen.has(key)) continue
        seen.add(key)
        out.push(clean)
      }
      return out
    },
    formatLocationCandidate(city) {
      const name = (city?.name || "").trim()
      if (!name) return ""

      const admin = (city?.admin1 || "").trim()
      const countryCode = (city?.country_code || "").trim().toUpperCase()
      const country = (city?.country || "").trim()

      if (admin && countryCode === "US") {
        return `${name}, ${admin}`
      }
      if (admin && countryCode && admin.toUpperCase() !== countryCode) {
        return `${name}, ${admin}, ${countryCode}`
      }
      if (countryCode) {
        return `${name}, ${countryCode}`
      }
      if (country) {
        return `${name}, ${country}`
      }
      return name
    },
    normalizeLocationCandidateForRequest(city, mode = "") {
      const normalizedMode = (mode || this.draftFilters.locationMode || "").trim().toLowerCase()
      if (normalizedMode === "country" && this.locationSourceMode === "muse") {
        const museName = (city?.name || "").trim()
        if (!museName) return ""
        if (museName.includes(",")) return museName
        const countryCode = (city?.country_code || "").trim().toUpperCase()
        return countryCode ? `${museName}, ${countryCode}` : museName
      }
      return this.formatLocationCandidate(city)
    },
    toOptionalNumber(value) {
      const numeric = Number(value)
      return Number.isFinite(numeric) ? numeric : null
    },
    buildLocationCandidates(rawCities, mode = "") {
      const candidates = []
      for (const [index, rawCity] of (rawCities || []).entries()) {
        const candidateValue = this.normalizeLocationCandidateForRequest(rawCity, mode)
        if (!candidateValue) continue

        candidates.push({
          value: candidateValue,
          key: candidateValue.toLowerCase(),
          raw_index: index,
          distance_miles: this.toOptionalNumber(rawCity?.distance_miles),
          observed_count: this.toOptionalNumber(rawCity?.observed_count) || 0,
        })
      }
      return candidates
    },
    orderLocationCandidates(candidates, mode = "") {
      const normalizedMode = (mode || "").trim().toLowerCase()
      const ordered = [...(candidates || [])]

      if (normalizedMode === "country") {
        ordered.sort((a, b) => {
          if (a.observed_count !== b.observed_count) {
            return b.observed_count - a.observed_count
          }
          return a.value.localeCompare(b.value)
        })
        return ordered
      }

      if (normalizedMode === "nearby" || normalizedMode === "manual") {
        ordered.sort((a, b) => {
          const aDistance = a.distance_miles === null ? Number.POSITIVE_INFINITY : a.distance_miles
          const bDistance = b.distance_miles === null ? Number.POSITIVE_INFINITY : b.distance_miles
          if (aDistance !== bDistance) {
            return aDistance - bDistance
          }
          return a.raw_index - b.raw_index
        })
        return ordered
      }

      return ordered
    },
    dedupeLocationCandidates(candidates) {
      const unique = []
      const seen = new Set()
      for (const candidate of candidates || []) {
        if (!candidate?.value || !candidate?.key) continue
        if (seen.has(candidate.key)) continue
        seen.add(candidate.key)
        unique.push(candidate)
      }
      return unique
    },
    buildPreflightLocationSelection(locationNames, mode = "") {
      const normalizedMode = (mode || "").trim().toLowerCase()
      const cap = Math.max(1, Number(this.maxLocationParams || 1))
      const fallbackCandidates = this.normalizeUnique(locationNames).map((value, index) => ({
        value,
        key: value.toLowerCase(),
        raw_index: index,
        distance_miles: null,
        observed_count: 0,
      }))
      const baseCandidates = this.locationPreviewCandidates.length
        ? this.locationPreviewCandidates
        : fallbackCandidates

      const orderedCandidates = this.orderLocationCandidates(baseCandidates, normalizedMode)
      const dedupedCandidates = this.dedupeLocationCandidates(orderedCandidates)

      const requestedCount = dedupedCandidates.length
      const selected = dedupedCandidates.slice(0, cap).map(candidate => candidate.value)
      const usedCount = selected.length
      const truncated = requestedCount > usedCount
      const strategy = normalizedMode === "country"
        ? "country-observed-count"
        : ((normalizedMode === "nearby" || normalizedMode === "manual") ? "distance-first" : "input-order")

      return {
        selected,
        requestedCount,
        usedCount,
        truncated,
        strategy,
      }
    },
    buildPostedAfterValue(filters) {
      const preset = (filters?.datePreset || "any").trim().toLowerCase()
      if (preset === "custom") {
        const customDate = (filters?.customAfterDate || "").trim()
        return /^\d{4}-\d{2}-\d{2}$/.test(customDate) ? customDate : ""
      }

      let days = 0
      if (preset === "today") days = 0
      if (preset === "3") days = 3
      if (preset === "7") days = 7
      if (preset === "30") days = 30
      if (preset === "any") return ""
      if (!POSTED_DATE_PRESETS.has(preset)) return ""

      const threshold = new Date()
      threshold.setHours(0, 0, 0, 0)
      threshold.setDate(threshold.getDate() - days)
      return threshold.toISOString().slice(0, 10)
    },
    normalizeCategoryValues(values) {
      const canonicalized = []
      for (const value of values || []) {
        const clean = (value || "").trim()
        if (!clean) continue
        const canonical = this.categoryLookup[clean.toLowerCase()]
        canonicalized.push(canonical || clean)
      }
      return this.normalizeUnique(canonicalized)
    },
    applyFilterMetadata(payload) {
      if (!payload || typeof payload !== "object") return

      const groups = Array.isArray(payload.category_groups) ? payload.category_groups : []
      if (groups.length) {
        this.categoryGroups = groups.map(group => ({
          key: (group.key || "").toString(),
          name: (group.name || "").toString(),
          muse_categories: Array.isArray(group.muse_categories) ? group.muse_categories.map(value => String(value || "").trim()).filter(Boolean) : []
        })).filter(group => group.name)

        const mapLookup = {}
        for (const group of this.categoryGroups) {
          mapLookup[group.name] = group
        }
          this.categoryMapLookup = mapLookup
        }

      const categoryValues = Array.isArray(payload.category_values)
        ? payload.category_values
          .map(item => String(item?.value || "").trim().replace(/\s+/g, " "))
          .filter(Boolean)
        : []
      if (categoryValues.length) {
        this.categoryOptions = this.normalizeUnique(categoryValues)
      } else if (this.categoryGroups.length) {
        this.categoryOptions = this.normalizeUnique(
          this.categoryGroups.flatMap(group => Array.isArray(group.muse_categories) ? group.muse_categories : [])
        )
      }

      const aliasMapRaw = payload.category_aliases && typeof payload.category_aliases === "object"
        ? payload.category_aliases
        : {}
      const lookup = {}
      const canonicalByLower = {}

      for (const option of this.categoryOptions) {
        const canonical = String(option || "").trim()
        if (!canonical) continue
        lookup[canonical.toLowerCase()] = canonical
        canonicalByLower[canonical.toLowerCase()] = canonical
      }
      for (const group of this.categoryGroups) {
        const canonical = String(group.name || "").trim()
        if (!canonical) continue
        lookup[canonical.toLowerCase()] = canonical
        canonicalByLower[canonical.toLowerCase()] = canonical
      }

      for (const [alias, rawCanonical] of Object.entries(aliasMapRaw)) {
        const normalizedAlias = String(alias || "").trim().toLowerCase()
        const normalizedCanonical = String(rawCanonical || "").trim()
        if (!normalizedAlias || !normalizedCanonical) continue
        const resolvedCanonical = canonicalByLower[normalizedCanonical.toLowerCase()] || normalizedCanonical
        lookup[normalizedAlias] = resolvedCanonical
      }
      this.categoryLookup = lookup

      const levelValues = Array.isArray(payload.level_values)
        ? payload.level_values.map(item => ({
          value: this.normalizeLevelForApi(item?.value || ""),
          label: String(item?.label || "").trim().replace(/\s+/g, " "),
          observedCount: Number(item?.observed_count || 0),
        })).filter(item => item.value && item.label)
        : []
      const legacyLevels = levelValues.length
        ? []
        : (Array.isArray(payload.levels) ? payload.levels.map(value => ({
          value: this.normalizeLevelForApi(value),
          label: this.formatLevelLabel(this.normalizeLevelForApi(value)),
          observedCount: 0,
        })).filter(item => item.value && item.label) : [])
      const nextLevelOptions = levelValues.length
        ? this.normalizeUnique(levelValues.map(option => option.value)).map((value) => {
          const match = levelValues.find(option => option.value === value)
          return match || { value, label: this.formatLevelLabel(value), observedCount: 0 }
        })
        : (legacyLevels.length
          ? this.normalizeUnique(legacyLevels.map(option => option.value)).map((value) => {
            const match = legacyLevels.find(option => option.value === value)
            return match || { value, label: this.formatLevelLabel(value), observedCount: 0 }
          })
          : DEFAULT_LEVEL_OPTIONS.map(option => ({ ...option })))
      if (nextLevelOptions.length) {
        this.levelOptions = nextLevelOptions
        const nextLevelLookup = {}
        const nextLevelLabelLookup = {}
        for (const option of nextLevelOptions) {
          nextLevelLookup[option.value.toLowerCase()] = option.value
          nextLevelLookup[option.label.toLowerCase()] = option.value
          nextLevelLabelLookup[option.value] = option.label
          nextLevelLabelLookup[option.value.toLowerCase()] = option.label
        }
        this.levelLookup = nextLevelLookup
        this.levelLabelLookup = nextLevelLabelLookup
      }

      const capValue = Number(payload.location_param_cap || 0)
      if (Number.isFinite(capValue) && capValue > 0) {
        this.maxLocationParams = Math.max(1, Math.floor(capValue))
      }

      const countryValues = Array.isArray(payload.country_values)
        ? payload.country_values
          .map(item => ({
            code: String(item?.code || "").trim().toUpperCase(),
            name: String(item?.name || item?.code || "").trim(),
            observed_count: Number(item?.observed_count || 0),
          }))
          .filter(item => item.code && item.name)
        : []
      this.countryOptions = buildCountryOptions(countryValues)
      if (!this.countryOptions.some(country => country.code === this.draftFilters.countryCode)) {
        const fallbackCountryCode = this.countryOptions[0]?.code || ALL_COUNTRIES_CODE
        this.draftFilters.countryCode = fallbackCountryCode
        this.appliedFilters.countryCode = fallbackCountryCode
      }

      const providerValues = Array.isArray(payload.provider_values)
        ? payload.provider_values
          .map(item => ({
            value: this.normalizeProviderValue(item?.value || ""),
            label: String(item?.label || item?.value || "").trim(),
            observedCount: Number(item?.observed_count || 0),
          }))
          .filter(item => item.value && item.label)
        : []
      this.providerOptions = providerValues
      if (
        this.normalizeProviderValue(this.draftFilters.provider)
        && !this.providerOptions.some(option => option.value === this.normalizeProviderValue(this.draftFilters.provider))
      ) {
        this.draftFilters.provider = ""
        this.appliedFilters.provider = ""
      }

      this.filterMetadataVersion = payload.metadata_version || ""
      this.filterMetadataHash = payload.metadata_hash || ""
    },
    async fetchFilterMetadata() {
      try {
        const payload = await this.fetchJson("/api/jobs/filter-metadata")
        this.applyFilterMetadata(payload)
      } catch (error) {
        console.error("Failed to load jobs filter metadata", error)
      }
    },
    async fetchProviderAttribution() {
      try {
        const payload = await this.fetchJson("/api/providers/attribution")
        const providers = Array.isArray(payload?.providers) ? payload.providers : []
        const next = {}
        for (const item of providers) {
          const provider = (item?.provider || "").toString().trim()
          if (!provider) continue
          next[provider] = item.attribution || {}
        }
        this.providerAttributionByName = next
      } catch (e) {
        console.error("Failed to load provider attribution", e)
        this.providerAttributionByName = {}
      }
    },
    async fetchCountryOptions() {
      this.countryOptions = buildCountryOptions(this.countryOptions)
    },
    normalizeLevelValues(values) {
      const canonicalized = []
      for (const value of values || []) {
        const clean = (value || "").trim()
        if (!clean) continue
        const canonical = this.levelLookup[clean.toLowerCase()] || LEVEL_VALUE_ALIASES[clean.toLowerCase()] || clean.toLowerCase()
        if (canonical) canonicalized.push(canonical)
      }
      return this.normalizeUnique(canonicalized)
    },
    normalizeLevelForApi(value) {
      const clean = (value || "").trim()
      if (!clean) return ""
      return this.levelLookup[clean.toLowerCase()] || LEVEL_VALUE_ALIASES[clean.toLowerCase()] || clean.toLowerCase()
    },
    openCategoryMenu() {
      this.categoryMenuOpen = true
      this.categoryActiveIndex = 0
      this.categoryInfo = ""
    },
    closeCategoryMenuSoon() {
      window.setTimeout(() => {
        this.categoryMenuOpen = false
      }, 120)
    },
    onCategoryInput() {
      this.categoryMenuOpen = true
      this.categoryActiveIndex = 0
      this.categoryInfo = ""
    },
    moveCategorySelection(step) {
      if (!this.filteredCategoryOptions.length) return
      const next = this.categoryActiveIndex + step
      if (next < 0) {
        this.categoryActiveIndex = this.filteredCategoryOptions.length - 1
        return
      }
      if (next >= this.filteredCategoryOptions.length) {
        this.categoryActiveIndex = 0
        return
      }
      this.categoryActiveIndex = next
    },
    addCategory(category) {
      const clean = (category || "").trim()
      if (!clean) return
      const canonical = this.categoryLookup[clean.toLowerCase()] || clean

      this.draftFilters.categories = this.normalizeUnique([
        ...(this.draftFilters.categories || []),
        canonical
      ])

      this.categoryInput = ""
      this.categoryActiveIndex = 0
      this.categoryMenuOpen = true
      this.categoryInfo = canonical === clean && !this.categoryLookup[clean.toLowerCase()]
        ? "Added exact category value."
        : ""
    },
    chooseCategoryFromInput() {
      const input = (this.categoryInput || "").trim()
      if (!input) return

      const exact = this.categoryLookup[input.toLowerCase()]
      if (exact) {
        this.addCategory(exact)
        return
      }

      if (this.filteredCategoryOptions.length === 1) {
        this.addCategory(this.filteredCategoryOptions[0])
        return
      }

      if (this.filteredCategoryOptions.length > 1) {
        const highlighted = this.filteredCategoryOptions[this.categoryActiveIndex] || this.filteredCategoryOptions[0]
        this.addCategory(highlighted)
        return
      }
      this.addCategory(input)
    },
    async activateNearbyMode() {
      this.setLocationMode("nearby")
      await this.useNearbyMe()
    },
    setLocationMode(mode) {
      if (!["nearby", "country", "manual"].includes(mode)) return
      if (this.draftFilters.locationMode === mode) return

      this.draftFilters.locationMode = mode
      this.locationPreviewNames = []
      this.locationPreviewCities = []
      this.locationPreviewCandidates = []
      this.locationPreviewCenter = null
      this.locationInfo = ""
      this.locationWarning = ""
      this.locationError = ""
      this.pretrimLocationNotice = ""
      this.publishDebugState("location-mode-changed")
    },
    publishDebugState(reason = "state-update") {
      publishCurrentPageDiagnostics({
        reason,
        loading: this.loading,
        error: this.error,
        page: this.page,
        pageSize: this.pageSize,
        totalPages: this.totalPages,
        totalJobs: this.totalJobs,
        totalsAreEstimated: this.totalsAreEstimated,
        hasNextPage: this.hasNextPage,
        locationMode: this.draftFilters.locationMode,
        locationPreviewCount: this.locationPreviewNames.length,
        appliedLocationCount: (this.appliedFilters.locationNames || []).length,
        categoryCount: (this.appliedFilters.categories || []).length,
        levelCount: (this.appliedFilters.levels || []).length,
        companyCount: (this.appliedFilters.companies || []).length,
        includeHybrid: this.appliedFilters.includeHybrid,
        includeRemote: this.appliedFilters.includeRemote,
        pretrimLocationNotice: this.pretrimLocationNotice,
        locationWarning: this.locationWarning,
        locationError: this.locationError,
        searchDiagnostics: this.lastSearchDiagnostics,
        apiSummary: this.lastApiSummary,
      })
    },
    openLevelMenu() {
      this.levelMenuOpen = true
      this.levelActiveIndex = 0
      this.levelInfo = ""
    },
    closeLevelMenuSoon() {
      window.setTimeout(() => {
        this.levelMenuOpen = false
      }, 120)
    },
    onLevelInput() {
      this.levelMenuOpen = true
      this.levelActiveIndex = 0
      this.levelInfo = ""
    },
    moveLevelSelection(step) {
      if (!this.filteredLevelOptions.length) return
      const next = this.levelActiveIndex + step
      if (next < 0) {
        this.levelActiveIndex = this.filteredLevelOptions.length - 1
        return
      }
      if (next >= this.filteredLevelOptions.length) {
        this.levelActiveIndex = 0
        return
      }
      this.levelActiveIndex = next
    },
    addLevel(level) {
      const canonical = this.normalizeLevelForApi(level)
      if (!canonical) return

      this.draftFilters.levels = this.normalizeUnique([
        ...(this.draftFilters.levels || []),
        canonical
      ])

      this.levelInput = ""
      this.levelActiveIndex = 0
      this.levelMenuOpen = true
      this.levelInfo = ""
    },
    chooseLevelFromInput() {
      const input = (this.levelInput || "").trim()
      if (!input) return

      const exact = this.levelLookup[input.toLowerCase()]
      if (exact) {
        this.addLevel(exact)
        return
      }

      if (this.filteredLevelOptions.length === 1) {
        this.addLevel(this.filteredLevelOptions[0].value)
        return
      }

      if (this.filteredLevelOptions.length > 1) {
        const highlighted = this.filteredLevelOptions[this.levelActiveIndex] || this.filteredLevelOptions[0]
        this.addLevel(highlighted.value)
        return
      }

      this.levelInfo = "Choose a valid level from suggestions."
    },
    addCustomFilterValue(target) {
      const input = this.companyInput
      const clean = (input || "").trim()
      if (!clean) return

      const existing = this.draftFilters[target] || []
      this.draftFilters[target] = this.normalizeUnique([...existing, clean])

      this.companyInput = ""
    },
    removeFilterValue(target, value) {
      this.draftFilters[target] = (this.draftFilters[target] || []).filter(item => item !== value)
    },
    openCityPreviewModal() {
      if (!this.locationPreviewNames.length) return
      this.cityPreviewModalOpen = true
    },
    setCitySortMode(mode) {
      if (["closest", "alpha", "reverse"].includes(mode)) {
        this.citySortMode = mode
      }
    },
    closeCityPreviewModal() {
      this.cityPreviewModalOpen = false
    },
    haversineMiles(lat1, lon1, lat2, lon2) {
      const toRadians = deg => deg * (Math.PI / 180)
      const earthRadiusMiles = 3958.7613

      const dLat = toRadians(lat2 - lat1)
      const dLon = toRadians(lon2 - lon1)
      const rLat1 = toRadians(lat1)
      const rLat2 = toRadians(lat2)

      const a = Math.sin(dLat / 2) ** 2
        + Math.cos(rLat1) * Math.cos(rLat2) * Math.sin(dLon / 2) ** 2
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
      return earthRadiusMiles * c
    },
    getBestKnownCenter() {
      if (this.resolvedLocation?.latitude && this.resolvedLocation?.longitude) {
        return this.resolvedLocation
      }
      const cached = getCachedLocation()
      if (cached?.latitude && cached?.longitude) {
        return cached
      }
      return null
    },
    handleGlobalKeydown(event) {
      if (event.key === "Escape" && this.cityPreviewModalOpen) {
        this.closeCityPreviewModal()
      }
    },
    milesToKm(value) {
      return value * 1.609344
    },
    kmToMiles(value) {
      return value * 0.621371
    },
    setRadiusUnit(unit) {
      const currentUnit = this.draftFilters.radiusUnit
      if (unit === currentUnit) return

      const current = Number(this.draftFilters.locationRadius || 0)
      const converted = unit === "km" ? this.milesToKm(current) : this.kmToMiles(current)
      this.draftFilters.radiusUnit = unit
      this.draftFilters.locationRadius = Math.max(1, Math.min(this.maxRadiusForUnit, Math.round(converted)))
    },
    async fetchJson(url) {
      const startedAt = performance.now()
      const response = await fetch(url)
      let payload = null
      try {
        payload = await response.json()
      } catch {
        payload = null
      }

      this.recordApiSummary({
        endpoint: url,
        status: response.status,
        ok: response.ok,
        latencyMs: Math.round(performance.now() - startedAt),
        payload,
      })

      if (!response.ok) {
        const detail = payload?.detail?.message || payload?.detail || payload?.message || `Request failed (${response.status})`
        throw new Error(detail)
      }

      return payload
    },
    makePayloadHash(payload) {
      try {
        const raw = JSON.stringify(payload || {})
        let hash = 0
        for (let index = 0; index < raw.length; index += 1) {
          hash = ((hash << 5) - hash) + raw.charCodeAt(index)
          hash |= 0
        }
        return Math.abs(hash).toString(16).padStart(8, "0")
      } catch {
        return ""
      }
    },
    recordApiSummary({ endpoint, status, ok, latencyMs, payload }) {
      const trimmedEndpoint = String(endpoint || "").replace(window.location.origin, "")
      this.lastApiSummary = {
        endpoint: trimmedEndpoint || "unknown",
        status: status ?? "",
        ok: ok === true,
        latencyMs: Number.isFinite(Number(latencyMs)) ? Number(latencyMs) : null,
        payloadHash: this.makePayloadHash(payload),
        observedAt: new Date().toISOString(),
      }
    },
    async detectViaIp() {
      this.locationError = ""
      this.locationWarning = ""
      this.locationBusy = true
      try {
        const payload = await this.fetchJson("/api/geolocation/ip")
        this.resolvedLocation = payload
        if (payload.city) {
          this.draftFilters.manualLocationQuery = `${payload.city}${payload.country_code ? `, ${payload.country_code}` : ""}`
        }
        setCachedLocation(payload)
        this.locationInfo = `Detected approximate location from IP: ${payload.city || "Unknown"} ${payload.country_code ? `(${payload.country_code})` : ""}`
      } catch (e) {
        this.locationError = "Automatic location lookup failed. Please enter ZIP or city manually."
        console.error("IP location lookup failed", e)
      } finally {
        this.locationBusy = false
      }
    },
    async useNearbyMe() {
      this.locationError = ""
      this.locationWarning = ""
      this.locationBusy = true

      try {
        const coords = await requestBrowserLocation()
        const reverse = await this.fetchJson(`/api/geolocation/reverse?latitude=${coords.latitude}&longitude=${coords.longitude}`)
        this.resolvedLocation = {
          ...reverse,
          latitude: coords.latitude,
          longitude: coords.longitude,
          source: "browser",
          accuracy_km: coords.accuracy ? Number(coords.accuracy) / 1000 : null
        }
        setCachedLocation(this.resolvedLocation)

        if (this.resolvedLocation.city) {
          this.draftFilters.manualLocationQuery = `${this.resolvedLocation.city}${this.resolvedLocation.country_code ? `, ${this.resolvedLocation.country_code}` : ""}`
        }
        this.locationInfo = "Using your current location for nearby city matching."
      } catch (e) {
        this.locationError = "Location permission denied or unavailable. You can enter ZIP/city manually instead."
        console.error("Browser geolocation failed", e)
      } finally {
        this.locationBusy = false
      }
    },
    async resolveFallbackLocation() {
      const text = (this.locationFallbackInput || "").trim()
      if (!text) return

      this.locationError = ""
      this.locationWarning = ""
      this.locationBusy = true
      try {
        const payload = await this.fetchJson(this.withOptionalCountryCode("/api/geolocation/geocode", this.draftFilters.countryCode, {
          q: text,
        }))
        this.resolvedLocation = payload
        setCachedLocation(payload)
        this.draftFilters.manualLocationQuery = payload.display_name || text
        this.locationInfo = `Using fallback location: ${payload.display_name || payload.city || text}`
      } catch (e) {
        this.locationError = "Could not resolve that ZIP/city. Try another format (e.g., 02108 or Boston, MA)."
        console.error("Fallback geocode failed", e)
      } finally {
        this.locationBusy = false
      }
    },
    async resolveManualCenter() {
      const query = (this.draftFilters.manualLocationQuery || "").trim()
      if (!query) {
        this.locationWarning = "Enter a ZIP code or city to search by manual radius."
        return null
      }

      const payload = await this.fetchJson(this.withOptionalCountryCode("/api/geolocation/geocode", this.draftFilters.countryCode, {
        q: query,
      }))
      this.resolvedLocation = payload
      setCachedLocation(payload)
      return payload
    },
    async resolveNearbyCenter() {
      if (this.resolvedLocation?.latitude && this.resolvedLocation?.longitude) {
        return this.resolvedLocation
      }

      const cached = getCachedLocation()
      if (cached?.latitude && cached?.longitude) {
        this.resolvedLocation = cached
        return cached
      }

      await this.detectViaIp()
      if (this.resolvedLocation?.latitude && this.resolvedLocation?.longitude) {
        return this.resolvedLocation
      }

      return null
    },
    async resolveLocationNamesFromDraft() {
      this.locationError = ""
      this.locationWarning = ""
      this.locationInfo = ""
      this.locationPreviewCandidates = []

      const mode = this.draftFilters.locationMode

      if (mode === "country") {
        if (this.isAllCountriesCode(this.draftFilters.countryCode)) {
          this.locationPreviewNames = []
          this.locationPreviewCities = []
          this.locationPreviewCandidates = []
          this.locationPreviewCenter = null
          this.locationInfo = "All Countries keeps the search broad, so there is no matched-place preview to load."
          return []
        }

        const payload = await this.fetchJson(this.withOptionalCountryCode("/api/geolocation/country-cities", this.draftFilters.countryCode, {
          limit: 200,
        }))
        const previewCities = (payload.locations || payload.cities || []).filter(city => city?.name)
        const candidates = this.dedupeLocationCandidates(
          this.orderLocationCandidates(this.buildLocationCandidates(previewCities, "country"), "country")
        )
        const names = candidates.map(candidate => candidate.value)
        this.locationPreviewCities = previewCities
        this.locationPreviewCandidates = candidates
        const center = this.getBestKnownCenter()
        this.locationPreviewCenter = center
          ? { latitude: center.latitude, longitude: center.longitude }
          : null
        this.locationPreviewNames = names
        if (!names.length) {
          this.locationWarning = "No supported locations found for that country right now."
        } else {
          this.locationInfo = `Using ${names.length} supported locations in ${this.getCountryName(this.draftFilters.countryCode)}.`
        }
        return names
      }

      const center = mode === "manual"
        ? await this.resolveManualCenter()
        : await this.resolveNearbyCenter()

      if (!center) {
        this.locationWarning = "Could not determine location center. Enter ZIP/city manually."
        this.locationPreviewNames = []
        this.locationPreviewCities = []
        this.locationPreviewCandidates = []
        this.locationPreviewCenter = null
        return []
      }

      const radiusValue = Number(this.draftFilters.locationRadius || 0)
      const radius = Math.max(1, Math.min(this.maxRadiusForUnit, radiusValue || 25))
      this.draftFilters.locationRadius = radius

      const payload = await this.fetchJson(this.withOptionalCountryCode("/api/geolocation/cities-in-radius", this.draftFilters.countryCode, {
        latitude: center.latitude,
        longitude: center.longitude,
        radius,
        unit: this.draftFilters.radiusUnit,
        limit: 240,
      }))

      const previewCities = (payload.cities || []).filter(city => city?.name)
      const candidates = this.dedupeLocationCandidates(
        this.orderLocationCandidates(this.buildLocationCandidates(previewCities, mode), mode)
      )
      const names = candidates.map(candidate => candidate.value)
      this.locationPreviewCities = previewCities
      this.locationPreviewCandidates = candidates
      this.locationPreviewCenter = {
        latitude: center.latitude,
        longitude: center.longitude
      }
      this.locationPreviewNames = names

      if (!names.length) {
        const fallbackName = center.city || this.draftFilters.manualLocationQuery || ""
        if (fallbackName) {
          this.locationPreviewCities = [{ name: fallbackName }]
          this.locationPreviewCandidates = [{
            value: fallbackName,
            key: fallbackName.toLowerCase(),
            raw_index: 0,
            distance_miles: 0,
            observed_count: 0,
          }]
          this.locationPreviewNames = [fallbackName]
          this.locationWarning = "No cities found in that radius, so only the center location will be used."
          return [fallbackName]
        }
        this.locationWarning = "No nearby cities found. Try a larger radius or country-wide mode."
        return []
      }

      this.locationInfo = `Matched ${names.length} cities near ${center.city || "your selected location"}.`
      return names
    },
    async previewLocationSelection() {
      this.locationBusy = true
      try {
        this.closeCityPreviewModal()
        await this.resolveLocationNamesFromDraft()
      } catch (e) {
        this.locationError = "Failed to preview matched places. Please try again."
        console.error("Location preview failed", e)
      } finally {
        this.locationBusy = false
      }
    },
    buildSearchQuery(page = 1) {
      const params = new URLSearchParams()
      params.set("page", String(page))
      params.set("page_size", String(this.pageSize))
      params.set("location_mode", this.appliedFilters.locationMode || "")
      params.set("sort_by", this.normalizeSortBy(this.appliedFilters.sortBy))

      const locationCountryCode = this.countryCodeForApi(this.appliedFilters.countryCode)
      if (locationCountryCode) {
        params.set("location_country_code", locationCountryCode)
      }

      for (const value of this.normalizeUnique(this.appliedFilters.categories)) {
        params.append("category", value)
      }
      for (const value of this.normalizeUnique(this.appliedFilters.levels)) {
        params.append("level", this.normalizeLevelForApi(value))
      }
      const normalizedLocations = this.normalizeUnique(this.appliedFilters.locationNames)
      for (const value of normalizedLocations) {
        params.append("location", value)
      }
      for (const value of this.normalizeUnique(this.appliedFilters.companies)) {
        params.append("company", value)
      }
      const provider = this.normalizeProviderValue(this.appliedFilters.provider)
      if (provider) {
        params.set("provider", provider)
      }
      const keyword = (this.appliedFilters.keyword || "").trim()
      if (keyword) {
        params.set("q", keyword)
      }
      const postedAfter = this.buildPostedAfterValue(this.appliedFilters)
      if (postedAfter) {
        params.set("posted_after", postedAfter)
      }

      params.set("include_remote", this.appliedFilters.includeRemote ? "true" : "false")
      params.set("include_hybrid", this.appliedFilters.includeHybrid ? "true" : "false")

      return params.toString()
    },
    async loadJobs(allowAutoClamp = true) {
      this.loading = true
      this.error = ""
      let debugReason = "jobs-loaded"

      try {
        const query = this.buildSearchQuery(this.page)
        const data = await this.fetchJson(`/api/jobs/search?${query}`)
        this.totalJobs = Number(data.total_jobs_estimated || data.total_jobs || 0)
        this.totalPages = Math.max(1, Number(data.total_pages_estimated || data.total_pages || 1))
        this.totalsAreEstimated = data.totals_are_estimated === true
        this.hasNextPage = data.has_next_page === true
        this.lastSearchDiagnostics = {
          totalEstimateStrategy: data.total_estimate_strategy || "",
          guardrailStopReason: data.guardrail_stop_reason || "",
          sourcePagesScanned: Number(data.source_pages_scanned || 0),
          filteredOutCount: Number(data.filtered_out_count || 0),
          requestedLocationCount: Number(data.requested_location_count || 0),
          usedLocationCount: Number(data.used_location_count || data.location_params_used || 0),
          locationParamsTruncated: data.location_params_truncated === true,
          hasNextPagePossibleRaw: data.has_next_page_possible_raw === true,
          hasMoreSourcePages: data.has_more_source_pages === true,
          sourcePageCount: Number(data.source_page_count || 0),
          windowStartPage: Number(data.window_start_page || 0),
          windowSize: Number(data.window_size || 0),
          locationSelectionStrategy: data.location_selection_strategy || "",
          canonicalizedLocationCount: Number(data.canonicalized_location_count || 0),
          transformedLocationCount: Number(data.transformed_location_count || 0),
          unmatchedLocationCount: Number(data.unmatched_location_count || 0),
          strictStateBlockedCount: Number(data.strict_state_blocked_count || 0),
          selectedStateDiversityCount: Number(data.selected_state_diversity_count || 0),
          acceptedByConcreteLocation: Number(data.accepted_by_concrete_location || 0),
          acceptedByRemoteOverride: Number(data.accepted_by_remote_override || 0),
          acceptedByHybridOverride: Number(data.accepted_by_hybrid_override || 0),
          acceptedByConstraintOverlap: Number(data.accepted_by_constraint_overlap || 0),
          constraintParseHighConfidence: Number(data.constraint_parse_high_confidence || 0),
          constraintParseMediumConfidence: Number(data.constraint_parse_medium_confidence || 0),
          constraintParseLowConfidence: Number(data.constraint_parse_low_confidence || 0),
          constraintPolicyRemoteOff: data.constraint_policy_remote_off || "",
          constraintCompatibilityEnabled: data.constraint_compatibility_enabled === true,
          constraintFilterMinConfidence: data.constraint_filter_min_confidence || "",
          adaptiveChaseEnabled: data.adaptive_chase_enabled === true,
          adaptiveChaseExtraPages: Number(data.adaptive_chase_extra_pages || 0),
          effectiveMaxPages: Number(data.effective_max_pages || 0),
          effectiveMinFilteredRatio: Number(data.effective_min_filtered_ratio || 0),
          droppedLocationCount: Number(data.dropped_location_count || 0),
          droppedLocationsSample: data.dropped_locations_sample || [],
          droppedInvalidUrlCount: Number(data.dropped_invalid_url_count || 0),
          urlValidationCheckedCount: Number(data.url_validation_checked_count || 0),
          urlValidationCacheHitCount: Number(data.url_validation_cache_hit_count || 0),
          locationRelaxedFallback: data.location_relaxed_fallback === true,
          requestedLocationsSample: data.requested_locations_sample || [],
          selectedLocationsSample: data.selected_locations_sample || [],
          cacheHit: data.cache_hit === true,
        }
        if (this.page > this.totalPages) {
          this.page = this.totalPages
        }
        if (data.location_params_truncated === true) {
          const used = Number(data.used_location_count || data.location_params_used || 0)
          const requested = Number(data.requested_location_count || used)
          const droppedSample = Array.isArray(data.dropped_locations_sample)
            ? data.dropped_locations_sample.slice(0, 3)
            : []
          const droppedHint = droppedSample.length
            ? ` Dropped examples: ${droppedSample.join(", ")}.`
            : ""
          this.locationLimitNotice = `Large location set detected. Backend used ${used} of ${requested} locations for stable results.${droppedHint}`
        } else {
          this.locationLimitNotice = ""
        }

        const mappedJobs = (data.jobs || []).map(job => ({
          id: job.id,
          provider: job.provider,
          title: job.name,
          short_name: job.short_name || "",
          company: job.company,
          location: job.locations?.[0] || "Unknown",
          location_country_code: job.location_country_code || "",
          location_country_name: job.location_country_name || "",
          locations: job.locations || [],
          level: job.levels?.[0] || "",
          levels: job.levels || [],
          categories: job.categories || [],
          tags: job.tags || [],
          type: job.type || "",
          model_type: job.model_type || "",
          work_mode_reason: job.work_mode_reason || "",
          has_remote: job.has_remote === true,
          has_hybrid: job.has_hybrid === true,
          is_local_compatible_remote: job.is_local_compatible_remote === true,
          local_compatibility_reason: job.local_compatibility_reason || "",
          location_constraints: job.location_constraints || {},
          publication_date: job.publication_date,
          short_description: job.short_description || "",
          apply_link: job.apply_url || job.job_url,
          link: job.job_url,
          contents: job.contents || ""
        }))

        this.jobs = mappedJobs

        if (allowAutoClamp && this.page > 1 && !this.jobs.length && !this.hasNextPage) {
          this.page = Math.max(1, this.page - 1)
          await this.loadJobs(false)
          return
        }
      } catch (e) {
        this.jobs = []
        this.error = "Failed to load jobs. Please try again."
        console.error("Failed to load jobs", e)
        this.lastSearchDiagnostics = {}
        debugReason = "jobs-load-error"
      } finally {
        this.loading = false
        try {
          await this.syncRouteQuery()
        } catch (routeError) {
          console.error("Failed to sync job board URL", routeError)
        }
        this.publishDebugState(debugReason)
      }
    },
    async applyFilters() {
      this.locationBusy = true
      try {
        const useResolvedLocationList = this.draftFilters.locationMode !== "country"
        const locationNames = useResolvedLocationList ? await this.resolveLocationNamesFromDraft() : []
        const preflightSelection = this.buildPreflightLocationSelection(locationNames, this.draftFilters.locationMode)
        this.pretrimLocationNotice = preflightSelection.requestedCount
          ? `Using ${preflightSelection.usedCount} of ${preflightSelection.requestedCount} resolved locations (${preflightSelection.strategy}).`
          : ""

        this.appliedFilters = this.cloneFilters(this.draftFilters)
        this.appliedFilters.categories = this.normalizeCategoryValues(this.appliedFilters.categories)
        this.appliedFilters.levels = this.normalizeLevelValues(this.appliedFilters.levels)
        this.appliedFilters.companies = this.normalizeUnique(this.appliedFilters.companies)
        this.appliedFilters.provider = this.normalizeProviderValue(this.appliedFilters.provider)
        this.appliedFilters.locationNames = preflightSelection.selected

        this.page = 1
        await this.loadJobs()
        this.publishDebugState("filters-applied")
      } catch (e) {
        this.locationError = "Failed to apply location filters. Please review your location settings."
        this.pretrimLocationNotice = ""
        console.error("Apply filters failed", e)
        this.publishDebugState("filters-apply-error")
      } finally {
        this.locationBusy = false
      }
    },
    async clearFilters() {
      this.draftFilters = this.createDefaultFilters()
      this.appliedFilters = this.createDefaultFilters()
      this.categoryInput = ""
      this.categoryInfo = ""
      this.categoryActiveIndex = 0
      this.categoryMenuOpen = false
      this.advancedFiltersOpen = false
      this.levelInput = ""
      this.levelInfo = ""
      this.levelActiveIndex = 0
      this.levelMenuOpen = false
      this.advancedLocationModalOpen = false
      this.cityPreviewModalOpen = false
      this.companyInput = ""
      this.locationFallbackInput = ""
      this.locationInfo = ""
      this.locationWarning = ""
      this.locationError = ""
      this.locationPreviewNames = []
      this.locationPreviewCities = []
      this.locationPreviewCandidates = []
      this.locationPreviewCenter = null
      this.resolvedLocation = null
      this.totalJobs = 0
      this.totalPages = 1
      this.totalsAreEstimated = false
      this.hasNextPage = false
      this.locationLimitNotice = ""
      this.pretrimLocationNotice = ""
      this.page = 1

      await this.loadJobs()
      this.publishDebugState("filters-cleared")
    },
    async goToNextPage() {
      if (!this.hasNextPage || this.loading) return
      this.page += 1
      await this.loadJobs()
    },
    async goToPreviousPage() {
      if (this.page <= 1 || this.loading) return
      this.page -= 1
      await this.loadJobs()
    },
    async goToPage(pageNumber) {
      const target = Number(pageNumber || 1)
      if (this.loading || target < 1 || target > this.totalPages || target === this.page) return
      this.page = target
      await this.loadJobs()
    }
  },
  async mounted() {
    window.addEventListener("keydown", this.handleGlobalKeydown)
    this.debugToolsUnsubscribe = subscribeDebugTools((state) => {
      this.showDebugTools = state.showDebugTools === true
    })
    await this.fetchFilterMetadata()
    await this.fetchProviderAttribution()
    await this.fetchCountryOptions()

    const cached = getCachedLocation()
    if (cached?.latitude && cached?.longitude) {
      this.resolvedLocation = cached
      this.locationInfo = `Saved nearby location available near ${cached.city || "your area"} if you want to switch from country-wide search.`
    }

    await this.hydrateFromRouteQuery(this.$route.query, "mounted")
  },
  beforeUnmount() {
    window.removeEventListener("keydown", this.handleGlobalKeydown)
    if (typeof this.debugToolsUnsubscribe === "function") {
      this.debugToolsUnsubscribe()
    }
    clearCurrentPageDiagnostics()
  }
}
</script>

<style scoped src="./css/Job-board.css"></style>

