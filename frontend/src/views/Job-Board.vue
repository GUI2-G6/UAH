<template>
    <div class="page">
        <div class="greeting">
            <h1>Job Board</h1>
            <p>Browse and apply to jobs in one click!</p>
        </div>

        <section class="filters">
            <div class="filter-grid">
                <div class="filter-group">
                    <label for="job-keyword">Keyword</label>
                    <input
                        id="job-keyword"
                        v-model.trim="draftFilters.keyword"
                        type="text"
                        placeholder="Title, company, location, category, level"
                    />
                </div>

                <div class="filter-group">
                    <label for="job-date-preset">Posted</label>
                    <select id="job-date-preset" v-model="draftFilters.datePreset">
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
                        v-model="draftFilters.customAfterDate"
                        type="date"
                    />
                </div>

                <div class="filter-group">
                    <label>Work Setup</label>
                    <div class="mode-row compact">
                      <button
                        type="button"
                        class="mode-button"
                        :class="{ active: draftFilters.includeHybrid }"
                        @click="draftFilters.includeHybrid = !draftFilters.includeHybrid"
                      >
                        Hybrid {{ draftFilters.includeHybrid ? 'On' : 'Off' }}
                      </button>
                      <button
                        type="button"
                        class="mode-button"
                        :class="{ active: draftFilters.includeRemote }"
                        @click="draftFilters.includeRemote = !draftFilters.includeRemote"
                      >
                        Remote {{ draftFilters.includeRemote ? 'On' : 'Off' }}
                      </button>
                    </div>
                    <p class="hint-text">Hybrid is enabled by default. Fully remote jobs are off by default.</p>
                </div>
            </div>

            <div class="filter-grid">
                <div class="filter-group">
                  <label for="job-categories">Categories</label>
                  <div class="category-selector">
                    <input
                      id="job-categories"
                      v-model.trim="categoryInput"
                      type="text"
                      autocomplete="off"
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
                    <select id="job-levels" v-model="draftFilters.levels" multiple>
                        <option v-for="option in levelOptions" :key="option" :value="option">
                            {{ option }}
                        </option>
                    </select>
                </div>

                <div class="filter-group">
                  <label>Location Mode</label>
                  <div class="mode-row">
                    <button
                      type="button"
                      class="mode-button"
                      :class="{ active: draftFilters.locationMode === 'manual' }"
                      @click="draftFilters.locationMode = 'manual'"
                    >
                      Manual
                    </button>
                    <button
                      type="button"
                      class="mode-button"
                      :class="{ active: draftFilters.locationMode === 'nearby' }"
                      @click="draftFilters.locationMode = 'nearby'"
                    >
                      Nearby Me
                    </button>
                    <button
                      type="button"
                      class="mode-button"
                      :class="{ active: draftFilters.locationMode === 'country' }"
                      @click="draftFilters.locationMode = 'country'"
                    >
                      Within My Country
                    </button>
                    </div>

                  <div v-if="draftFilters.locationMode === 'manual'" class="mode-panel">
                    <input
                      id="job-location-query"
                      v-model.trim="draftFilters.manualLocationQuery"
                      type="text"
                      placeholder="ZIP code or city (e.g., 02108 or Boston, MA)"
                    />
                  </div>

                  <div v-if="draftFilters.locationMode === 'nearby'" class="mode-panel">
                    <div class="custom-input-row">
                      <button type="button" @click="useNearbyMe" :disabled="locationBusy">
                        Use Current Location
                      </button>
                      <button type="button" @click="detectViaIp" :disabled="locationBusy">
                        Refresh Approximate Location
                      </button>
                    </div>

                    <p class="hint-text" v-if="resolvedLocation">
                      Center: {{ resolvedLocation.city || 'Unknown city' }} {{ resolvedLocation.country_code ? `(${resolvedLocation.country_code})` : '' }}
                    </p>

                    <div class="custom-input-row">
                      <input
                        v-model.trim="locationFallbackInput"
                        type="text"
                        placeholder="If detection fails, enter ZIP/city"
                        @keyup.enter="resolveFallbackLocation"
                      />
                      <button type="button" @click="resolveFallbackLocation" :disabled="locationBusy">
                        Use ZIP/City
                      </button>
                    </div>
                  </div>

                  <div v-if="draftFilters.locationMode === 'country'" class="mode-panel">
                    <select v-model="draftFilters.countryCode">
                      <option v-for="country in countryOptions" :key="country.code" :value="country.code">
                        {{ country.name }}
                      </option>
                    </select>
                  </div>

                  <div v-if="draftFilters.locationMode !== 'country'" class="mode-panel">
                    <label for="job-radius">Radius</label>
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

                  <div class="custom-input-row">
                    <button type="button" @click="previewLocationSelection" :disabled="locationBusy">
                      {{ locationBusy ? 'Resolving area...' : 'Preview Area Cities' }}
                    </button>
                  </div>

                  <p class="hint-text" v-if="locationInfo">{{ locationInfo }}</p>
                  <p class="error-text" v-if="locationError">{{ locationError }}</p>
                  <p class="warn-text" v-if="locationWarning">{{ locationWarning }}</p>

                  <div class="city-preview" v-if="locationPreviewNames.length">
                    <div class="city-preview-header">
                      <strong>Area Cities ({{ locationPreviewNames.length }})</strong>
                    </div>
                    <ul class="city-preview-list">
                      <li
                        v-for="city in visibleLocationPreviewNames"
                        :key="`preview-city-${city}`"
                      >
                        {{ city }}
                      </li>
                    </ul>
                    <button
                      v-if="hasMorePreviewCities"
                      type="button"
                      class="city-preview-more"
                      @click="openCityPreviewModal"
                    >
                      Show {{ hiddenLocationPreviewCount }} more
                    </button>
                  </div>
                </div>
            </div>

            <div class="filter-grid">
                <div class="filter-group full-width">
                    <label for="job-company-input">Company filters</label>
                    <div class="custom-input-row">
                        <input
                            id="job-company-input"
                            v-model.trim="companyInput"
                            type="text"
                            placeholder="Add company and press Add"
                            @keyup.enter="addCustomFilterValue('companies')"
                        />
                        <button type="button" @click="addCustomFilterValue('companies')">Add</button>
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

            <div class="filter-actions">
                <button type="button" class="primary" @click="applyFilters" :disabled="loading">
                    Apply Filters
                </button>
                <button type="button" class="secondary" @click="clearFilters" :disabled="loading">
                    Clear All
                </button>
            </div>
        </section>

        <div
          v-if="cityPreviewModalOpen"
          class="city-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="All area cities"
          @click="closeCityPreviewModal"
        >
          <div class="city-modal-dialog" @click.stop>
            <div class="city-modal-header">
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

        <div class="jobs-meta">
            <p v-if="loading">Loading jobs...</p>
            <p v-else-if="error" class="error-text">{{ error }}</p>
            <p v-else>Showing {{ jobs.length }} jobs</p>
        </div>

        <div class="dashboard">
            <div class="empty-state" v-if="!loading && !error && !jobs.length">
                No jobs matched the selected filters.
            </div>
            <JobPosting
                v-else
                v-for="job in jobs"
                :key="job.id"
                :job="job"
            />
        </div>
    </div>
</template>


<script>
import JobPosting from "../components/JobPosting.vue";
import {
  getCachedLocation,
  requestBrowserLocation,
  setCachedLocation
} from "../lib/geolocation";

export default {
  name: "JobBoard",
  components: { JobPosting },
  data() {
    const categoryOptions = [
      "Accounting",
      "Accounting and Finance",
      "Account Management",
      "Account Management/Customer Success",
      "Administration and Office",
      "Advertising and Marketing",
      "Animal Care",
      "Arts",
      "Business Operations",
      "Cleaning and Facilities",
      "Computer and IT",
      "Construction",
      "Corporate",
      "Customer Service",
      "Data and Analytics",
      "Data Science",
      "Design",
      "Design and UX",
      "Editor",
      "Education",
      "Energy Generation and Mining",
      "Entertainment and Travel Services",
      "Farming and Outdoors",
      "Food and Hospitality Services",
      "Healthcare",
      "HR",
      "Human Resources and Recruitment",
      "Installation, Maintenance, and Repairs",
      "IT",
      "Law",
      "Legal Services",
      "Management",
      "Manufacturing and Warehouse",
      "Marketing",
      "Mechanic",
      "Media, PR, and Communications",
      "Mental Health",
      "Nurses",
      "Office Administration",
      "Personal Care and Services",
      "Physical Assistant",
      "Product",
      "Product Management",
      "Project Management",
      "Protective Services",
      "Public Relations",
      "Real Estate",
      "Recruiting",
      "Retail",
      "Sales",
      "Science and Engineering",
      "Social Services",
      "Software Engineer",
      "Software Engineering",
      "Sports, Fitness, and Recreation",
      "Transportation and Logistics",
      "Unknown",
      "UX",
      "Videography",
      "Writer",
      "Writing and Editing"
    ]

    const categoryAliases = {
      "software engineer": "Software Engineer",
      "software engineering": "Software Engineering",
      "human resources": "Human Resources and Recruitment",
      "hr": "HR",
      "it": "IT",
      "ux": "UX",
      "pr": "Public Relations"
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
      "management"
    ]

    const countryOptions = [
      { code: "US", name: "United States" },
      { code: "CA", name: "Canada" },
      { code: "GB", name: "United Kingdom" },
      { code: "DE", name: "Germany" },
      { code: "FR", name: "France" }
    ]

    const defaultFilters = {
      categories: [],
      levels: [],
      includeHybrid: true,
      includeRemote: false,
      locationMode: "nearby",
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
      loading: false,
      error: "",
      page: 1,
      categoryOptions,
      categoryLookup,
      levelOptions,
      countryOptions,
      categoryInput: "",
      categoryInfo: "",
      categoryMenuOpen: false,
      categoryActiveIndex: 0,
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
      locationPreviewCenter: null,
      resolvedLocation: null,
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
    visibleLocationPreviewNames() {
      return (this.locationPreviewNames || []).slice(0, this.cityPreviewVisibleLimit)
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
    }
  },
  methods: {
    createDefaultFilters() {
      return {
        categories: [],
        levels: [],
        includeHybrid: true,
        includeRemote: false,
        locationMode: "nearby",
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
    normalizeCategoryValues(values) {
      const canonicalized = []
      for (const value of values || []) {
        const clean = (value || "").trim()
        if (!clean) continue
        const canonical = this.categoryLookup[clean.toLowerCase()]
        if (canonical) canonicalized.push(canonical)
      }
      return this.normalizeUnique(canonicalized)
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
      const canonical = this.categoryLookup[(category || "").trim().toLowerCase()]
      if (!canonical) return

      this.draftFilters.categories = this.normalizeUnique([
        ...(this.draftFilters.categories || []),
        canonical
      ])

      this.categoryInput = ""
      this.categoryActiveIndex = 0
      this.categoryMenuOpen = true
      this.categoryInfo = ""
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

      this.categoryInfo = "Choose a valid Muse category from suggestions."
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

      const mode = this.draftFilters.locationMode

      if (mode === "country") {
        const payload = await this.fetchJson(`/api/geolocation/country-cities?country_code=${encodeURIComponent(this.draftFilters.countryCode)}&limit=140`)
        const previewCities = (payload.cities || []).filter(city => city?.name)
        const names = this.normalizeUnique(previewCities.map(city => city.name))
        this.locationPreviewCities = previewCities
        const center = this.getBestKnownCenter()
        this.locationPreviewCenter = center
          ? { latitude: center.latitude, longitude: center.longitude }
          : null
        this.locationPreviewNames = names
        if (!names.length) {
          this.locationWarning = "No country-wide city data found for that country yet."
        } else {
          this.locationInfo = `Using ${names.length} cities in ${this.draftFilters.countryCode}.`
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
      const names = this.normalizeUnique(previewCities.map(city => city.name))
      this.locationPreviewCities = previewCities
      this.locationPreviewCenter = {
        latitude: center.latitude,
        longitude: center.longitude
      }
      this.locationPreviewNames = names

      if (!names.length) {
        const fallbackName = center.city || this.draftFilters.manualLocationQuery || ""
        if (fallbackName) {
          this.locationPreviewCities = [{ name: fallbackName }]
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

      for (const value of this.normalizeUnique(this.appliedFilters.categories)) {
        params.append("category", value)
      }
      for (const value of this.normalizeUnique(this.appliedFilters.levels)) {
        params.append("level", value)
      }
      for (const value of this.normalizeUnique(this.appliedFilters.locationNames)) {
        params.append("location", value)
      }
      for (const value of this.normalizeUnique(this.appliedFilters.companies)) {
        params.append("company", value)
      }

      return params.toString()
    },
    applyClientFilters(inputJobs) {
      let filtered = [...inputJobs]
      const keyword = this.appliedFilters.keyword.trim().toLowerCase()

      if (keyword) {
        filtered = filtered.filter(job => {
          const metadata = [
            job.title,
            job.company,
            ...(job.locations || []),
            ...(job.categories || []),
            ...(job.levels || [])
          ]
          return metadata
            .join(" ")
            .toLowerCase()
            .includes(keyword)
        })
      }

      filtered = filtered.filter(job => {
        const includeHybrid = this.appliedFilters.includeHybrid !== false
        const includeRemote = this.appliedFilters.includeRemote === true
        const hasHybrid = job.has_hybrid === true
        const hasRemote = job.has_remote === true
        const isRemoteOnly = hasRemote && !hasHybrid

        if (!includeHybrid && hasHybrid) {
          return false
        }
        if (!includeRemote && isRemoteOnly) {
          return false
        }
        return true
      })

      const preset = this.appliedFilters.datePreset
      const now = new Date()
      let threshold = null

      if (preset === "7") {
        threshold = new Date(now)
        threshold.setDate(now.getDate() - 7)
      } else if (preset === "30") {
        threshold = new Date(now)
        threshold.setDate(now.getDate() - 30)
      } else if (preset === "custom" && this.appliedFilters.customAfterDate) {
        threshold = new Date(`${this.appliedFilters.customAfterDate}T00:00:00`)
      }

      if (threshold) {
        filtered = filtered.filter(job => {
          if (!job.publication_date) return false
          const postedDate = new Date(job.publication_date)
          return !Number.isNaN(postedDate.getTime()) && postedDate >= threshold
        })
      }

      return filtered
    },
    async loadJobs() {
      this.loading = true
      this.error = ""

      try {
        const query = this.buildSearchQuery(this.page)
        const res = await fetch(`/api/jobs/search?${query}`)
        if (!res.ok) {
          throw new Error(`Request failed (${res.status})`)
        }

        const data = await res.json()
        const mappedJobs = (data.jobs || []).map(job => ({
          id: job.id,
          title: job.name,
          company: job.company,
          location: job.locations?.[0] || "Unknown",
          locations: job.locations || [],
          level: job.levels?.[0] || "",
          levels: job.levels || [],
          categories: job.categories || [],
          has_remote: job.has_remote === true,
          has_hybrid: job.has_hybrid === true,
          publication_date: job.publication_date,
          link: job.job_url
        }))

        this.jobs = this.applyClientFilters(mappedJobs)
      } catch (e) {
        this.jobs = []
        this.error = "Failed to load jobs. Please try again."
        console.error("Failed to load jobs", e)
      } finally {
        this.loading = false
      }
    },
    async applyFilters() {
      this.locationBusy = true
      try {
        const locationNames = await this.resolveLocationNamesFromDraft()

        this.appliedFilters = this.cloneFilters(this.draftFilters)
        this.appliedFilters.categories = this.normalizeCategoryValues(this.appliedFilters.categories)
        this.appliedFilters.levels = this.normalizeUnique(this.appliedFilters.levels)
        this.appliedFilters.companies = this.normalizeUnique(this.appliedFilters.companies)
        this.appliedFilters.locationNames = this.normalizeUnique(locationNames)

        this.page = 1
        await this.loadJobs()
      } catch (e) {
        this.locationError = "Failed to apply location filters. Please review your location settings."
        console.error("Apply filters failed", e)
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
      this.cityPreviewModalOpen = false
      this.companyInput = ""
      this.locationFallbackInput = ""
      this.locationInfo = ""
      this.locationWarning = ""
      this.locationError = ""
      this.locationPreviewNames = []
      this.locationPreviewCities = []
      this.locationPreviewCenter = null
      this.page = 1

      await this.loadJobs()
    }
  },
  async mounted() {
    window.addEventListener("keydown", this.handleGlobalKeydown)

    const cached = getCachedLocation()
    if (cached?.latitude && cached?.longitude) {
      this.resolvedLocation = cached
      this.locationInfo = `Using cached location near ${cached.city || "your area"}.`
      await this.applyFilters()
      return
    }

    await this.detectViaIp()
    if (this.resolvedLocation?.latitude && this.resolvedLocation?.longitude) {
      await this.applyFilters()
      return
    }

    await this.loadJobs()
  },
  beforeUnmount() {
    window.removeEventListener("keydown", this.handleGlobalKeydown)
  }
}
</script>

<style scoped src="./css/Job-board.css"></style>