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
            </div>

            <div class="filter-grid">
                <div class="filter-group">
                    <label for="job-categories">Categories</label>
                    <select id="job-categories" v-model="draftFilters.categories" multiple>
                        <option v-for="option in categoryOptions" :key="option" :value="option">
                            {{ option }}
                        </option>
                    </select>
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
                    <label for="job-locations">Locations</label>
                    <select id="job-locations" v-model="draftFilters.locations" multiple>
                        <option v-for="option in locationOptions" :key="option" :value="option">
                            {{ option }}
                        </option>
                    </select>
                    <div class="custom-input-row">
                        <input
                            v-model.trim="locationInput"
                            type="text"
                            placeholder="Add custom location"
                            @keyup.enter="addCustomFilterValue('locations')"
                        />
                        <button type="button" @click="addCustomFilterValue('locations')">Add</button>
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

export default {
  name: "JobBoard",
  components: { JobPosting },
  data() {
    const categoryOptions = [
      "Data Science",
      "Design and UX",
      "IT",
      "Science and Engineering",
      "Software Engineering",
      "Product",
      "Project Management"
    ]

    const levelOptions = [
      "Internship",
      "Entry Level",
      "Mid Level",
      "Senior Level",
      "management"
    ]

    const locationOptions = [
      "Remote",
      "Boston, MA",
      "New York, NY",
      "San Francisco, CA",
      "Ann Arbor, MI"
    ]

    const defaultFilters = {
      categories: [],
      levels: [],
      locations: [],
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
      levelOptions,
      locationOptions,
      companyInput: "",
      locationInput: "",
      draftFilters: JSON.parse(JSON.stringify(defaultFilters)),
      appliedFilters: JSON.parse(JSON.stringify(defaultFilters))
    };
  },
  methods: {
    createDefaultFilters() {
      return {
        categories: [],
        levels: [],
        locations: [],
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
      for (const value of values || []) {
        const clean = (value || "").trim()
        if (!clean) continue
        if (!out.includes(clean)) out.push(clean)
      }
      return out
    },
    addCustomFilterValue(target) {
      const isLocationTarget = target === "locations"
      const input = isLocationTarget ? this.locationInput : this.companyInput
      const clean = (input || "").trim()
      if (!clean) return

      const existing = this.draftFilters[target] || []
      this.draftFilters[target] = this.normalizeUnique([...existing, clean])

      if (isLocationTarget) this.locationInput = ""
      else this.companyInput = ""
    },
    removeFilterValue(target, value) {
      this.draftFilters[target] = (this.draftFilters[target] || []).filter(item => item !== value)
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
      for (const value of this.normalizeUnique(this.appliedFilters.locations)) {
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
      this.appliedFilters = this.cloneFilters(this.draftFilters)
      this.appliedFilters.categories = this.normalizeUnique(this.appliedFilters.categories)
      this.appliedFilters.levels = this.normalizeUnique(this.appliedFilters.levels)
      this.appliedFilters.locations = this.normalizeUnique(this.appliedFilters.locations)
      this.appliedFilters.companies = this.normalizeUnique(this.appliedFilters.companies)

      this.page = 1
      await this.loadJobs()
    },
    async clearFilters() {
      this.draftFilters = this.createDefaultFilters()
      this.appliedFilters = this.createDefaultFilters()
      this.companyInput = ""
      this.locationInput = ""
      this.page = 1

      await this.loadJobs()
    }
  },
  async mounted() {
    await this.loadJobs()
  }
}
</script>

<style scoped src="./css/Job-board.css"></style>