<template>
    <div class="page job-board-page">
        <div class="greeting job-board-hero">
            <div>
                <h1>Job Board</h1>
                <p>Start broad, then narrow only when you need to.</p>
            </div>
            <div class="hero-copy">
                <span class="hero-chip">Broad-first search</span>
                <p>Default results search across {{ selectedCountryName }} with remote and hybrid roles included.</p>
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
                        <p class="hint-text">Pick a suggested group or type a custom Muse category and press Enter.</p>

                        <div class="custom-input-row">
                          <button type="button" class="secondary-action" @click="openCategoryMappingModal" :disabled="!draftFilters.categories.length">
                            View group mapping
                          </button>
                        </div>

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
                            placeholder="Search levels"
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
                              :key="option"
                              type="button"
                              class="category-option"
                              :class="{ active: index === levelActiveIndex }"
                              @mousedown.prevent="addLevel(option)"
                            >
                              {{ option }}
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
                              :title="`Remove ${level}`"
                            >
                              {{ level }} x
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
                            {{ country.name }}{{ country.location_count ? ` (${country.location_count})` : '' }}
                          </option>
                        </select>
                        <p class="hint-text">Country mode stays broad. Nearby and custom location use this as a boundary when available.</p>
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
                        <label>Area preview</label>
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
          @clear="clearFilters"
          @remove-chip="removeActiveFilterChip"
          @widen="widenSearch"
        />

        <JobBoardDebugPanel
          v-if="showDebugTools"
          :diagnostics="lastSearchDiagnostics"
          :pretrim-location-notice="pretrimLocationNotice"
          :filter-metadata-version="filterMetadataVersion"
          :filter-metadata-hash="filterMetadataHash"
        />

        <div class="pagination pagination-top" v-if="!loading && !error">
          <button type="button" @click="goToPreviousPage" :disabled="page <= 1 || loading">Previous</button>
          <button
            type="button"
            v-for="pageNumber in visiblePageButtons"
            :key="`jobs-page-top-${pageNumber}`"
            :class="{ active: pageNumber === page }"
            @click="goToPage(pageNumber)"
            :disabled="loading"
          >
            {{ pageNumber }}
          </button>
          <span>of {{ totalPages }}{{ totalsAreEstimated ? ' est.' : '' }}</span>
          <button type="button" @click="goToNextPage" :disabled="!hasNextPage || loading">Next</button>
        </div>

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

        <div class="pagination pagination-bottom" v-if="!loading && !error">
            <button type="button" @click="goToPreviousPage" :disabled="page <= 1 || loading">Previous</button>
            <button
              type="button"
              v-for="pageNumber in visiblePageButtons"
              :key="`jobs-page-${pageNumber}`"
              :class="{ active: pageNumber === page }"
              @click="goToPage(pageNumber)"
              :disabled="loading"
            >
              {{ pageNumber }}
            </button>
            <span>of {{ totalPages }}{{ totalsAreEstimated ? ' est.' : '' }}</span>
            <button type="button" @click="goToNextPage" :disabled="!hasNextPage || loading">Next</button>
        </div>

        <div
          v-if="categoryMappingModalOpen"
          class="city-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Category mapping"
          @click="closeCategoryMappingModal"
        >
          <div class="city-modal-dialog" v-draggable-modal="{ handle: '.city-modal-header' }" @click.stop>
            <div class="city-modal-header drag-handle">
              <h2>Category Group Mapping</h2>
              <button type="button" class="city-modal-close" @click="closeCategoryMappingModal">Close</button>
            </div>
            <p class="city-modal-subtitle">Selected groups expand to these Muse categories during API search.</p>
            <div class="city-modal-scroll">
              <ul class="city-modal-list">
                <li v-for="group in selectedCategoryGroups" :key="`cat-map-${group.name}`">
                  <strong>{{ group.name }}</strong>: {{ group.muse_categories.join(', ') }}
                </li>
                <li v-for="custom in selectedCustomCategories" :key="`cat-custom-${custom}`">
                  <strong>{{ custom }}</strong>: used as a direct Muse category query value.
                </li>
              </ul>
            </div>
            <div class="city-modal-actions">
              <button type="button" @click="closeCategoryMappingModal">Close</button>
            </div>
          </div>
        </div>

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
              <h2>Area Cities</h2>
              <button type="button" class="city-modal-close" @click="closeCityPreviewModal">Close</button>
            </div>

            <p class="city-modal-subtitle">Showing all {{ locationPreviewNames.length }} matched cities.</p>

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
import {
  getCachedLocation,
  requestBrowserLocation,
  setCachedLocation
} from "../lib/geolocation";
import { publishCurrentPageDiagnostics, clearCurrentPageDiagnostics } from "../lib/debugDiagnostics";
import { subscribeDebugTools } from "../lib/debugTools";

export default {
  name: "JobBoard",
  components: {
    JobPosting,
    JobBoardPrimaryFilters,
    JobBoardResultsSummary,
    JobBoardDebugPanel,
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

    const categoryOptions = categoryGroups.map(group => group.name)

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
    for (const [alias, canonical] of Object.entries(categoryAliases)) {
      categoryLookup[alias] = canonical
    }

    const levelOptions = [
      "Internship",
      "Entry Level",
      "Mid Level",
      "Senior Level",
      "Management"
    ]

    const levelLookup = {}
    for (const value of levelOptions) {
      levelLookup[value.toLowerCase()] = value
    }

    const categoryMapLookup = {}
    for (const group of categoryGroups) {
      categoryMapLookup[group.name] = group
    }

    const countryOptions = [{ code: "US", name: "United States", location_count: 0 }]

    const defaultFilters = {
      categories: [],
      levels: [],
      includeHybrid: true,
      includeRemote: true,
      locationMode: "country",
      locationRadius: 25,
      radiusUnit: "mi",
      manualLocationQuery: "",
      countryCode: "US",
      locationNames: [],
      companies: [],
      keyword: "",
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
      maxLocationParams,
      locationSourceMode,
      categoryGroups,
      categoryMapLookup,
      categoryOptions,
      categoryLookup,
      levelOptions,
      levelLookup,
      countryOptions,
      categoryInput: "",
      categoryInfo: "",
      categoryMenuOpen: false,
      categoryActiveIndex: 0,
      categoryMappingModalOpen: false,
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
        if (selected.has(option.toLowerCase())) return false
        if (!query) return true
        return option.toLowerCase().includes(query)
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
    locationPreviewSummary() {
      if (!this.locationPreviewNames.length) return ""
      if (this.draftFilters.locationMode === "country") {
        return `Previewing ${this.locationPreviewNames.length} supported locations in ${this.getCountryName(this.draftFilters.countryCode)}.`
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
        chips.push({ key: `level-${level}`, type: "level", value: level, label: `Level: ${level}` })
      }
      for (const company of filters.companies || []) {
        chips.push({ key: `company-${company}`, type: "company", value: company, label: `Company: ${company}` })
      }

      const keyword = String(filters.keyword || "").trim()
      if (keyword) {
        chips.push({ key: "keyword", type: "keyword", value: "", label: `Keyword: ${keyword}` })
      }

      const datePreset = String(filters.datePreset || "any").trim().toLowerCase()
      if (datePreset !== "any") {
        const label = datePreset === "custom"
          ? `After: ${filters.customAfterDate || "custom date"}`
          : `Posted: last ${datePreset} days`
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
          label: `Location set (${filters.locationNames.length})`,
        })
      }

      return chips
    },
    canWidenSearch() {
      const filters = this.appliedFilters || {}
      const hasCountryMode = (filters.locationMode || "").trim().toLowerCase() === "country"
      const hasBroadWorkSetup = filters.includeRemote === true && filters.includeHybrid === true
      return !(hasCountryMode && hasBroadWorkSetup)
    },
    searchScopeSummary() {
      const filters = this.appliedFilters || {}
      const workSetup = this.buildWorkSetupSummary(filters)

      if ((filters.locationMode || "").trim().toLowerCase() === "country") {
        return `Searching across ${this.getCountryName(filters.countryCode)} with ${workSetup}.`
      }

      const selectedCount = (filters.locationNames || []).length
      if (selectedCount > 0) {
        const centerName = this.resolvedLocation?.city || filters.manualLocationQuery || "your selected area"
        return `Searching around ${centerName} across ${selectedCount} matched locations with ${workSetup}.`
      }

      return `Searching with ${workSetup}.`
    }
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
        countryCode: "US",
        locationNames: [],
        companies: [],
        keyword: "",
        datePreset: "any",
        customAfterDate: ""
      }
    },
    cloneFilters(filters) {
      return JSON.parse(JSON.stringify(filters))
    },
    getCountryName(code) {
      const normalized = String(code || "").trim().toUpperCase()
      const match = (this.countryOptions || []).find(country => country.code === normalized)
      return match?.name || normalized || "your country"
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
      if (preset === "7") days = 7
      if (preset === "30") days = 30
      if (!days) return ""

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
        this.categoryOptions = this.categoryGroups.map(group => group.name)
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

      for (const [alias, rawCanonical] of Object.entries(aliasMapRaw)) {
        const normalizedAlias = String(alias || "").trim().toLowerCase()
        const normalizedCanonical = String(rawCanonical || "").trim()
        if (!normalizedAlias || !normalizedCanonical) continue
        const resolvedCanonical = canonicalByLower[normalizedCanonical.toLowerCase()] || normalizedCanonical
        lookup[normalizedAlias] = resolvedCanonical
      }
      this.categoryLookup = lookup

      const levels = Array.isArray(payload.levels) ? payload.levels.map(level => String(level || "").trim()).filter(Boolean) : []
      if (levels.length) {
        this.levelOptions = levels
        const nextLevelLookup = {}
        for (const level of levels) {
          nextLevelLookup[level.toLowerCase()] = level
        }
        this.levelLookup = nextLevelLookup
      }

      const capValue = Number(payload.location_param_cap || 0)
      if (Number.isFinite(capValue) && capValue > 0) {
        this.maxLocationParams = Math.max(1, Math.floor(capValue))
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
      try {
        if (this.locationSourceMode !== "muse") {
          return
        }
        const payload = await this.fetchJson("/api/geolocation/muse-supported-countries")
        const countries = (payload.countries || [])
          .filter(country => country?.code)
          .map(country => ({
            code: country.code,
            name: country.name || country.code,
            location_count: Number(country.location_count || 0)
          }))

        if (!countries.length) {
          this.locationWarning = "Muse country coverage is still loading. Try again shortly."
          return
        }

        this.countryOptions = countries
        if (!countries.some(country => country.code === this.draftFilters.countryCode)) {
          this.draftFilters.countryCode = countries[0].code
        }
      } catch (error) {
        this.locationWarning = "Could not load Muse country coverage."
        console.error("Failed to load Muse countries", error)
      }
    },
    normalizeLevelValues(values) {
      const canonicalized = []
      for (const value of values || []) {
        const clean = (value || "").trim()
        if (!clean) continue
        const canonical = this.levelLookup[clean.toLowerCase()]
        if (canonical) canonicalized.push(canonical)
      }
      return this.normalizeUnique(canonicalized)
    },
    normalizeLevelForApi(value) {
      const canonical = this.levelLookup[(value || "").trim().toLowerCase()] || (value || "").trim()
      if (canonical.toLowerCase() === "management") {
        return "management"
      }
      return canonical
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
        ? "Added custom category value."
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
    openCategoryMappingModal() {
      if (!this.selectedCategoryGroups.length) return
      this.categoryMappingModalOpen = true
    },
    closeCategoryMappingModal() {
      this.categoryMappingModalOpen = false
    },
    openAdvancedLocationModal() {
      this.advancedLocationModalOpen = true
    },
    closeAdvancedLocationModal() {
      this.advancedLocationModalOpen = false
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
      const canonical = this.levelLookup[(level || "").trim().toLowerCase()]
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
        this.addLevel(this.filteredLevelOptions[0])
        return
      }

      if (this.filteredLevelOptions.length > 1) {
        const highlighted = this.filteredLevelOptions[this.levelActiveIndex] || this.filteredLevelOptions[0]
        this.addLevel(highlighted)
        return
      }

      this.levelInfo = "Choose a valid Muse level from suggestions."
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
      if (event.key === "Escape" && this.categoryMappingModalOpen) {
        this.closeCategoryMappingModal()
      }
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
      const response = await fetch(url)
      let payload = null
      try {
        payload = await response.json()
      } catch {
        payload = null
      }

      if (!response.ok) {
        const detail = payload?.detail?.message || payload?.detail || payload?.message || `Request failed (${response.status})`
        throw new Error(detail)
      }

      return payload
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
        const payload = await this.fetchJson(`/api/geolocation/geocode?q=${encodeURIComponent(text)}&country_code=${encodeURIComponent(this.draftFilters.countryCode || "")}`)
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

      const payload = await this.fetchJson(`/api/geolocation/geocode?q=${encodeURIComponent(query)}&country_code=${encodeURIComponent(this.draftFilters.countryCode || "")}`)
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
        const endpoint = this.locationSourceMode === "muse"
          ? "/api/geolocation/muse-supported-locations"
          : "/api/geolocation/country-cities"

        const payload = await this.fetchJson(`${endpoint}?country_code=${encodeURIComponent(this.draftFilters.countryCode)}&limit=200`)
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
          this.locationWarning = "No Muse-supported locations found for that country right now."
        } else {
          this.locationInfo = `Using ${names.length} Muse-supported locations in ${this.draftFilters.countryCode}.`
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

      const payload = await this.fetchJson(
        `/api/geolocation/cities-in-radius?latitude=${encodeURIComponent(center.latitude)}&longitude=${encodeURIComponent(center.longitude)}&radius=${encodeURIComponent(radius)}&unit=${encodeURIComponent(this.draftFilters.radiusUnit)}&country_code=${encodeURIComponent(this.draftFilters.countryCode || "")}&limit=240`
      )

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
        this.locationError = "Failed to preview area cities. Please try again."
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

      const locationCountryCode = (this.appliedFilters.countryCode || "").trim().toUpperCase()
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
        const res = await fetch(`/api/jobs/search?${query}`)
        if (!res.ok) {
          throw new Error(`Request failed (${res.status})`)
        }

        const data = await res.json()
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
      this.categoryMappingModalOpen = false
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

    await this.loadJobs()
    this.publishDebugState("mounted")
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

