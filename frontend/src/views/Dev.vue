<template>
  <section class="dev-console">
    <header class="dev-console-header">
      <div>
        <p class="dev-eyebrow">Developer diagnostics</p>
        <h1>Job Board Operator Console</h1>
        <p class="dev-subtitle">
          Probe real Job Board endpoints, inspect structured DB health, and compare browser-observed requests with
          server-side diagnostics.
        </p>
      </div>
      <div class="dev-header-actions">
        <button type="button" class="secondary-btn" @click="refreshOverview" :disabled="overviewLoading">
          {{ overviewLoading ? 'Refreshing overview...' : 'Refresh overview' }}
        </button>
        <button type="button" class="secondary-btn" @click="refreshDbInsights" :disabled="dbLoading">
          {{ dbLoading ? 'Refreshing DB...' : 'Refresh DB insights' }}
        </button>
        <button type="button" class="primary-btn" @click="refreshAll" :disabled="overviewLoading || dbLoading">
          Refresh all
        </button>
      </div>
    </header>

    <div v-if="pageError" class="dev-banner error">
      {{ pageError }}
    </div>

    <div v-else-if="overview && overview.database?.dedup?.active_collision_count > 0" class="dev-banner warning">
      Active dedup collisions detected: {{ overview.database.dedup.active_collision_count }}
    </div>

    <div v-else-if="overview" class="dev-banner ok">
      Job board diagnostics are healthy. No active dedup collisions are currently reported.
    </div>

    <section class="dev-section">
      <div class="section-header">
        <div>
          <p class="section-eyebrow">Overview</p>
          <h2>Provider status, quota, syncs, and compact health</h2>
        </div>
      </div>

      <div v-if="overviewLoading && !overview" class="empty-state">Loading job board overview...</div>

      <template v-else-if="overview">
        <div class="card-grid">
          <article class="metric-card">
            <span class="metric-label">Active jobs</span>
            <strong>{{ formatNumber(overview.database?.counts?.active_jobs) }}</strong>
          </article>
          <article class="metric-card">
            <span class="metric-label">Inactive jobs</span>
            <strong>{{ formatNumber(overview.database?.counts?.inactive_jobs) }}</strong>
          </article>
          <article class="metric-card">
            <span class="metric-label">Bad provider URLs</span>
            <strong>{{ formatNumber(overview.database?.counts?.bad_provider_urls) }}</strong>
          </article>
          <article class="metric-card">
            <span class="metric-label">Bad apply URLs</span>
            <strong>{{ formatNumber(overview.database?.counts?.bad_apply_urls) }}</strong>
          </article>
          <article class="metric-card">
            <span class="metric-label">Stale jobs</span>
            <strong>{{ formatNumber(overview.database?.counts?.stale_jobs) }}</strong>
          </article>
          <article class="metric-card">
            <span class="metric-label">Dedup collisions</span>
            <strong>{{ formatNumber(overview.database?.dedup?.active_collision_count) }}</strong>
          </article>
        </div>

        <div class="two-column-grid">
          <article class="panel-card">
            <div class="panel-header">
              <h3>Providers</h3>
              <span class="panel-note">
                Display enabled: {{ (overview.providers?.display_enabled || []).join(', ') || 'none' }}
              </span>
            </div>
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Provider</th>
                    <th>Status</th>
                    <th>Display</th>
                    <th>Ingest</th>
                    <th>Schedule</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="provider in overview.providers?.statuses || []" :key="provider.provider">
                    <td>{{ provider.provider }}</td>
                    <td><span class="pill" :class="toneClass(provider.status)">{{ provider.status }}</span></td>
                    <td>{{ provider.display_enabled ? 'on' : 'off' }}</td>
                    <td>{{ provider.ingest_enabled ? 'on' : 'off' }}</td>
                    <td>{{ provider.scheduled_enabled ? 'on' : 'off' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>

          <article class="panel-card">
            <div class="panel-header">
              <h3>Quota usage</h3>
              <span class="panel-note">Latest hourly rows</span>
            </div>
            <div v-if="!(overview.quota_usage || []).length" class="empty-state compact">No quota rows yet.</div>
            <ul v-else class="stack-list">
              <li v-for="row in overview.quota_usage || []" :key="`${row.provider}-${row.hour_bucket}`">
                <strong>{{ row.provider }}</strong>
                <span>{{ formatNumber(row.request_count) }} requests</span>
                <span>{{ formatTimestamp(row.hour_bucket) }}</span>
              </li>
            </ul>
          </article>
        </div>

        <article class="panel-card">
          <div class="panel-header">
            <h3>Recent syncs</h3>
            <span class="panel-note">Latest provider/category runs</span>
          </div>
          <div v-if="!(overview.recent_syncs || []).length" class="empty-state compact">No sync logs yet.</div>
          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Category</th>
                  <th>Started</th>
                  <th>Pages</th>
                  <th>Found</th>
                  <th>Updated</th>
                  <th>Deduped</th>
                  <th>Stopped</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in overview.recent_syncs || []" :key="entry.id">
                  <td>{{ entry.provider }}</td>
                  <td>{{ entry.category || 'global' }}</td>
                  <td>{{ formatTimestamp(entry.started_at) }}</td>
                  <td>{{ formatNumber(entry.pages_fetched) }}</td>
                  <td>{{ formatNumber(entry.jobs_found) }}</td>
                  <td>{{ formatNumber(entry.jobs_updated) }}</td>
                  <td>{{ formatNumber(entry.jobs_deduplicated) }}</td>
                  <td>{{ entry.stopped_reason || 'completed' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </template>
    </section>

    <section class="dev-section">
      <div class="section-header">
        <div>
          <p class="section-eyebrow">API probes</p>
          <h2>Manually confirm endpoint responsiveness</h2>
        </div>
      </div>

      <div class="probe-grid">
        <article class="panel-card">
          <div class="panel-header">
            <h3>Quick GET probes</h3>
          </div>
          <div class="action-row">
            <button type="button" class="secondary-btn" @click="probeFilterMetadata" :disabled="probeBusy">
              Probe filter metadata
            </button>
            <button type="button" class="secondary-btn" @click="probeProviderAttribution" :disabled="probeBusy">
              Probe provider attribution
            </button>
          </div>
        </article>

        <article class="panel-card">
          <div class="panel-header">
            <h3>Local search probe</h3>
            <span class="panel-note">Replays `/api/jobs/search`</span>
          </div>
          <textarea v-model="localSearchProbeJson" class="json-input" spellcheck="false"></textarea>
          <button type="button" class="primary-btn" @click="probeLocalSearch" :disabled="probeBusy">
            Run local search probe
          </button>
        </article>

        <article class="panel-card">
          <div class="panel-header">
            <h3>Live search probe</h3>
            <span class="panel-note">Replays `/api/jobs/search-live-source`</span>
          </div>
          <textarea v-model="liveSearchProbeJson" class="json-input" spellcheck="false"></textarea>
          <button type="button" class="primary-btn" @click="probeLiveSearch" :disabled="probeBusy">
            Run live search probe
          </button>
        </article>

        <article class="panel-card">
          <div class="panel-header">
            <h3>Provider probe</h3>
            <span class="panel-note">One bounded upstream provider call</span>
          </div>
          <label class="field-label" for="provider-select">Provider</label>
          <select id="provider-select" v-model="providerProbeProvider" class="field-input">
            <option v-for="provider in providerOptions" :key="provider" :value="provider">{{ provider }}</option>
          </select>
          <textarea v-model="providerProbeParamsJson" class="json-input" spellcheck="false"></textarea>
          <button type="button" class="primary-btn" @click="probeProvider" :disabled="probeBusy">
            Run provider probe
          </button>
        </article>

        <article class="panel-card">
          <div class="panel-header">
            <h3>Gmail scan simulation</h3>
            <span class="panel-note">Developer-only fake ATS messages classifier check</span>
          </div>
          <textarea v-model="gmailDebugProbeJson" class="json-input" spellcheck="false"></textarea>
          <button type="button" class="secondary-btn" @click="backfillApplySessionsFromSaved" :disabled="probeBusy">
            Backfill apply sessions from saved jobs
          </button>
          <button type="button" class="primary-btn" @click="probeGmailSimulateScan" :disabled="probeBusy">
            Run Gmail simulation
          </button>
        </article>
      </div>

      <article class="panel-card">
        <div class="panel-header">
          <h3>Probe results</h3>
          <span class="panel-note">Most recent first</span>
        </div>
        <div v-if="!probeResults.length" class="empty-state compact">Run a probe to capture status, latency, and payload preview.</div>
        <div v-else class="probe-results">
          <div v-for="result in probeResults" :key="result.id" class="probe-result-card">
            <div class="probe-result-head">
              <div>
                <strong>{{ result.label }}</strong>
                <p>{{ result.url }}</p>
              </div>
              <div class="probe-metrics">
                <span class="pill" :class="result.ok ? 'healthy' : 'unhealthy'">{{ result.status }}</span>
                <span>{{ result.latencyMs }} ms</span>
              </div>
            </div>
            <div class="probe-json-grid">
              <div>
                <span class="json-label">Request</span>
                <pre>{{ formatJson(result.requestBody) }}</pre>
              </div>
              <div>
                <span class="json-label">Response</span>
                <pre>{{ formatJson(result.responseBody) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="dev-section">
      <div class="section-header">
        <div>
          <p class="section-eyebrow">DB insights</p>
          <h2>Targeted samples for pinpointing job-board issues</h2>
        </div>
        <input
          v-model.trim="insightFilter"
          class="insight-search"
          type="text"
          placeholder="Filter provider, title, company, location, or hash"
        />
      </div>

      <div v-if="dbLoading && !dbInsights" class="empty-state">Loading DB insights...</div>

      <template v-else-if="dbInsights">
        <div class="card-grid">
          <article class="metric-card">
            <span class="metric-label">Recent inserts</span>
            <strong>{{ formatNumber((dbInsights.recent_inserts || []).length) }}</strong>
          </article>
          <article class="metric-card">
            <span class="metric-label">Recent updates</span>
            <strong>{{ formatNumber((dbInsights.recent_updates || []).length) }}</strong>
          </article>
          <article class="metric-card">
            <span class="metric-label">Bad provider URLs</span>
            <strong>{{ formatNumber((dbInsights.bad_provider_urls || []).length) }}</strong>
          </article>
          <article class="metric-card">
            <span class="metric-label">Bad apply URLs</span>
            <strong>{{ formatNumber((dbInsights.bad_apply_urls || []).length) }}</strong>
          </article>
          <article class="metric-card">
            <span class="metric-label">Stale samples</span>
            <strong>{{ formatNumber((dbInsights.stale_jobs || []).length) }}</strong>
          </article>
          <article class="metric-card">
            <span class="metric-label">Dedup owners</span>
            <strong>{{ formatNumber((dbInsights.dedup_owners || []).length) }}</strong>
          </article>
        </div>

        <div class="insight-grid">
          <article v-for="section in filteredInsightSections" :key="section.key" class="panel-card">
            <div class="panel-header">
              <h3>{{ section.label }}</h3>
              <span class="panel-note">{{ formatNumber(section.rows.length) }} rows</span>
            </div>
            <div v-if="!section.rows.length" class="empty-state compact">No rows match the current filter.</div>
            <ul v-else class="job-sample-list">
              <li v-for="row in section.rows" :key="row.id || `${section.key}-${row.provider}-${row.provider_job_id}`">
                <div class="job-sample-header">
                  <strong>{{ row.title || row.provider || 'Untitled row' }}</strong>
                  <span>{{ row.provider }} · {{ row.provider_job_id || row.category || 'n/a' }}</span>
                </div>
                <p>{{ row.company || 'Unknown company' }} · {{ row.location || row.stopped_reason || 'n/a' }}</p>
                <p class="job-sample-meta">
                  {{ row.display_tier || row.started_at || 'n/a' }}
                  <span v-if="row.dedup_hash"> · {{ row.dedup_hash }}</span>
                  <span v-if="row.provider_url_status"> · provider {{ row.provider_url_status }}</span>
                  <span v-if="row.apply_url_status"> · apply {{ row.apply_url_status }}</span>
                </p>
              </li>
            </ul>
          </article>
        </div>
      </template>
    </section>

    <section class="dev-section">
      <div class="section-header">
        <div>
          <p class="section-eyebrow">Recent requests</p>
          <h2>Browser-observed traffic plus current page diagnostics</h2>
        </div>
      </div>

      <div class="two-column-grid">
        <article class="panel-card">
          <div class="panel-header">
            <h3>Observed requests</h3>
          </div>
          <div v-if="!(debugSnapshot.recentRequests || []).length" class="empty-state compact">
            No requests captured yet for this browser session.
          </div>
          <ul v-else class="stack-list">
            <li v-for="(request, index) in debugSnapshot.recentRequests || []" :key="`${request.url}-${request.at}-${index}`">
              <strong>{{ request.method }} {{ request.url }}</strong>
              <span>Status: {{ request.status }}</span>
              <span>Latency: {{ request.durationMs }} ms</span>
            </li>
          </ul>
        </article>

        <article class="panel-card">
          <div class="panel-header">
            <h3>Page diagnostics snapshot</h3>
          </div>
          <pre class="snapshot-pre">{{ formatJson(debugSnapshot.pageDiagnostics || {}) }}</pre>
        </article>
      </div>
    </section>
  </section>
</template>

<script>
import { authedFetch, syncCurrentUser } from '../lib/auth.js'
import {
  clearCurrentPageDiagnostics,
  publishCurrentPageDiagnostics,
  subscribeDebugState,
} from '../lib/debugDiagnostics'

export default {
  name: 'Dev',
  data() {
    return {
      overview: null,
      dbInsights: null,
      pageError: '',
      overviewLoading: false,
      dbLoading: false,
      probeBusy: false,
      probeResults: [],
      debugSnapshot: {},
      debugUnsubscribe: null,
      insightFilter: '',
      localSearchProbeJson: JSON.stringify(
        {
          params: {
            page: 1,
            page_size: 5,
            category: ['tech'],
            location: ['United States'],
            tier: 'active',
            q: 'engineer',
          },
        },
        null,
        2,
      ),
      liveSearchProbeJson: JSON.stringify(
        {
          params: {
            page: 1,
            page_size: 5,
            category: ['sales and marketing'],
            location_mode: 'country',
            location_country_code: 'US',
            include_remote: true,
            include_hybrid: true,
          },
        },
        null,
        2,
      ),
      providerProbeProvider: 'the_muse',
      providerProbeParamsJson: JSON.stringify(
        {
          page: 1,
          category: ['Sales'],
        },
        null,
        2,
      ),
      gmailDebugProbeJson: JSON.stringify(
        {
          require_ats: true,
          include_unsubmitted: false,
          messages: [
            {
              from: 'Acme Recruiting <noreply@acme.greenhouse.io>',
              subject: 'Interview next steps at Acme Robotics',
              snippet: 'We would like to schedule your interview for Software Engineer.',
              date: 'Mon, 28 Apr 2026 10:00:00 -0400',
            },
          ],
        },
        null,
        2,
      ),
    }
  },
  computed: {
    providerOptions() {
      return (this.overview?.providers?.statuses || []).map((provider) => provider.provider)
    },
    filteredInsightSections() {
      const filter = (this.insightFilter || '').trim().toLowerCase()
      const sections = [
        { key: 'recent_syncs', label: 'Recent syncs', rows: this.dbInsights?.recent_syncs || [] },
        { key: 'recent_inserts', label: 'Recent inserts', rows: this.dbInsights?.recent_inserts || [] },
        { key: 'recent_updates', label: 'Recent updates', rows: this.dbInsights?.recent_updates || [] },
        { key: 'bad_provider_urls', label: 'Bad provider URLs', rows: this.dbInsights?.bad_provider_urls || [] },
        { key: 'bad_apply_urls', label: 'Bad apply URLs', rows: this.dbInsights?.bad_apply_urls || [] },
        { key: 'stale_jobs', label: 'Stale jobs', rows: this.dbInsights?.stale_jobs || [] },
        { key: 'dedup_owners', label: 'Dedup owners', rows: this.dbInsights?.dedup_owners || [] },
      ]

      if (!filter) return sections

      return sections.map((section) => ({
        ...section,
        rows: section.rows.filter((row) => JSON.stringify(row).toLowerCase().includes(filter)),
      }))
    },
  },
  async mounted() {
    this.debugUnsubscribe = subscribeDebugState((snapshot) => {
      this.debugSnapshot = snapshot || {}
    })

    try {
      await syncCurrentUser({ force: true })
      await this.refreshAll()
    } catch (error) {
      this.pageError = error?.message || 'Unable to load developer diagnostics.'
    }
  },
  beforeUnmount() {
    if (typeof this.debugUnsubscribe === 'function') {
      this.debugUnsubscribe()
    }
    clearCurrentPageDiagnostics()
  },
  methods: {
    toneClass(status) {
      if (status === 'healthy' || status === 'active') return 'healthy'
      if (status === 'degraded' || status === 'partial') return 'warning'
      return 'unhealthy'
    },
    formatNumber(value) {
      return Number(value || 0).toLocaleString()
    },
    formatTimestamp(value) {
      if (!value) return 'n/a'
      const date = new Date(value)
      return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
    },
    formatJson(value) {
      return JSON.stringify(value ?? {}, null, 2)
    },
    parseJsonInput(rawValue, label) {
      try {
        return JSON.parse(rawValue)
      } catch (error) {
        throw new Error(`${label} is not valid JSON`)
      }
    },
    async authedJson(url, options = {}) {
      const response = await authedFetch(url, options)
      let payload = null
      try {
        payload = await response.json()
      } catch {
        payload = null
      }
      if (!response.ok) {
        const detail = payload?.detail || payload?.message || `Request failed (${response.status})`
        throw new Error(detail)
      }
      return payload
    },
    publishDebugState(reason = 'dev-console-update') {
      publishCurrentPageDiagnostics({
        reason,
        overviewLoaded: Boolean(this.overview),
        dbInsightsLoaded: Boolean(this.dbInsights),
        recentRequestCount: (this.debugSnapshot.recentRequests || []).length,
        probeResultCount: this.probeResults.length,
        dedupCollisions: this.overview?.database?.dedup?.active_collision_count || 0,
        pageError: this.pageError,
      })
    },
    async refreshOverview() {
      this.overviewLoading = true
      this.pageError = ''
      try {
        this.overview = await this.authedJson('/api/jobs/debug/overview')
        if (!this.providerProbeProvider && (this.providerOptions || []).length) {
          this.providerProbeProvider = this.providerOptions[0]
        }
      } catch (error) {
        this.pageError = error?.message || 'Unable to load job board overview.'
      } finally {
        this.overviewLoading = false
        this.publishDebugState('overview-refreshed')
      }
    },
    async refreshDbInsights() {
      this.dbLoading = true
      this.pageError = ''
      try {
        this.dbInsights = await this.authedJson('/api/jobs/debug/db-insights')
      } catch (error) {
        this.pageError = error?.message || 'Unable to load DB insights.'
      } finally {
        this.dbLoading = false
        this.publishDebugState('db-insights-refreshed')
      }
    },
    async refreshAll() {
      await Promise.all([this.refreshOverview(), this.refreshDbInsights()])
    },
    pushProbeResult(result) {
      this.probeResults.unshift({
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        ...result,
      })
      this.probeResults = this.probeResults.slice(0, 10)
      this.publishDebugState('probe-finished')
    },
    async runGetProbe(label, url) {
      this.probeBusy = true
      const startedAt = performance.now()
      try {
        const payload = await this.authedJson(url)
        this.pushProbeResult({
          label,
          url,
          status: 200,
          ok: true,
          latencyMs: Math.round(performance.now() - startedAt),
          requestBody: null,
          responseBody: payload,
        })
      } catch (error) {
        this.pushProbeResult({
          label,
          url,
          status: 'error',
          ok: false,
          latencyMs: Math.round(performance.now() - startedAt),
          requestBody: null,
          responseBody: { error: error?.message || String(error) },
        })
      } finally {
        this.probeBusy = false
      }
    },
    async runPostProbe(label, url, body) {
      this.probeBusy = true
      const startedAt = performance.now()
      try {
        const payload = await this.authedJson(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        this.pushProbeResult({
          label,
          url,
          status: payload?.status || 200,
          ok: payload?.status !== 'error',
          latencyMs: Math.round(performance.now() - startedAt),
          requestBody: body,
          responseBody: payload,
        })
      } catch (error) {
        this.pushProbeResult({
          label,
          url,
          status: 'error',
          ok: false,
          latencyMs: Math.round(performance.now() - startedAt),
          requestBody: body,
          responseBody: { error: error?.message || String(error) },
        })
      } finally {
        this.probeBusy = false
      }
    },
    async probeFilterMetadata() {
      await this.runGetProbe('Filter metadata', '/api/jobs/filter-metadata')
    },
    async probeProviderAttribution() {
      await this.runGetProbe('Provider attribution', '/api/providers/attribution')
    },
    async probeLocalSearch() {
      const payload = this.parseJsonInput(this.localSearchProbeJson, 'Local search probe payload')
      await this.runPostProbe('Local search probe', '/api/jobs/debug/probe/local-search', payload)
    },
    async probeLiveSearch() {
      const payload = this.parseJsonInput(this.liveSearchProbeJson, 'Live search probe payload')
      await this.runPostProbe('Live search probe', '/api/jobs/debug/probe/live-search', payload)
    },
    async probeProvider() {
      const params = this.parseJsonInput(this.providerProbeParamsJson, 'Provider probe params')
      await this.runPostProbe('Provider probe', '/api/jobs/debug/probe/provider', {
        provider: this.providerProbeProvider,
        params,
      })
    },
    async probeGmailSimulateScan() {
      const payload = this.parseJsonInput(this.gmailDebugProbeJson, 'Gmail simulation payload')
      await this.runPostProbe('Gmail simulation', '/api/integrations/gmail/debug/simulate-scan', payload)
    },
    async backfillApplySessionsFromSaved() {
      await this.runPostProbe('Apply-session backfill', '/api/apply-sessions/backfill-from-saved', {})
    },
  },
}
</script>

<style scoped src="./css/Dev.css"></style>
