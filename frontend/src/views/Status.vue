<template>
  <div class="status-page">
    <div class="page-header">
      <h2>System Status</h2>
      <div class="header-actions">
        <button class="back-btn" @click="goBack" type="button">
          Back
        </button>
        <span class="last-checked" v-if="lastChecked">
          Last checked: {{ lastChecked }}
        </span>
        <button class="refresh-btn" @click="fetchDiagnostics" :disabled="loading">
          {{ loading ? 'Checking...' : 'Refresh' }}
        </button>
      </div>
    </div>

    <div v-if="diagnostics" class="overall-banner" :class="diagnostics.overall">
      <span class="overall-dot" :class="diagnostics.overall"></span>
      <span class="overall-text">
        {{ diagnostics.overall === 'healthy' ? 'All Systems Operational' :
          diagnostics.overall === 'degraded' ? 'Partial Degradation' :
          'System Issues Detected' }}
      </span>
    </div>
    <div v-else-if="accessState === 'admin-required'" class="overall-banner degraded">
      <span class="overall-dot degraded"></span>
      <span class="overall-text">Admin sign-in required for backend diagnostics</span>
    </div>
    <div v-else-if="accessState === 'signin-required'" class="overall-banner degraded">
      <span class="overall-dot degraded"></span>
      <span class="overall-text">Sign in with an admin account to view backend diagnostics</span>
    </div>
    <div v-else-if="error" class="overall-banner unhealthy">
      <span class="overall-dot unhealthy"></span>
      <span class="overall-text">Unable to reach backend</span>
    </div>

    <div v-if="loading && !diagnostics" class="loading-state">
      <div class="spinner"></div>
      <p>Running diagnostics...</p>
    </div>

    <div v-if="diagnostics || accessState !== 'ok'" class="service-grid">
      <div class="service-card" v-if="accessState !== 'ok'">
        <div class="card-header">
          <h3>
            <span class="dot yellow"></span>
            Diagnostics Access
          </h3>
          <span class="badge degraded">
            limited
          </span>
        </div>
        <p v-if="accessState === 'signin-required'">
          Backend diagnostics are protected. Sign in with an admin account to inspect backend, database, and network health.
        </p>
        <p v-else-if="accessState === 'admin-required'">
          You are signed in, but this account does not have admin privileges for the diagnostics endpoint.
        </p>
        <p v-else>
          Diagnostics access is currently limited.
        </p>
      </div>

      <div class="service-card" v-if="diagnostics?.services?.backend">
        <div class="card-header">
          <h3>
            <span
              class="dot"
              :class="diagnostics.services.backend.status === 'healthy' ? 'green' : 'red'"
            ></span>
            Backend
          </h3>
          <span class="badge" :class="diagnostics.services.backend.status">
            {{ diagnostics.services.backend.status }}
          </span>
        </div>
        <table class="info-table">
          <tbody>
            <tr>
              <td class="label">Service</td>
              <td>
                {{ diagnostics.services.backend.name }} v{{ diagnostics.services.backend.version }}
              </td>
            </tr>
            <tr>
              <td class="label">Framework</td>
              <td>{{ diagnostics.services.backend.framework }}</td>
            </tr>
            <tr>
              <td class="label">Python</td>
              <td>{{ diagnostics.services.backend.python_version }}</td>
            </tr>
            <tr>
              <td class="label">Platform</td>
              <td>{{ diagnostics.services.backend.platform }}</td>
            </tr>
            <tr>
              <td class="label">PID</td>
              <td>{{ diagnostics.services.backend.pid }}</td>
            </tr>
            <tr>
              <td class="label">Container</td>
              <td><code>{{ diagnostics.services.backend.host }}</code></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="service-card" v-if="diagnostics?.services?.database">
        <div class="card-header">
          <h3>
            <span
              class="dot"
              :class="diagnostics.services.database.status === 'healthy' ? 'green' : 'red'"
            ></span>
            Database
          </h3>
          <span class="badge" :class="diagnostics.services.database.status">
            {{ diagnostics.services.database.status }}
          </span>
        </div>
        <table class="info-table" v-if="diagnostics.services.database.status === 'healthy'">
          <tbody>
            <tr>
              <td class="label">Engine</td>
              <td>{{ diagnostics.services.database.postgres_version }}</td>
            </tr>
            <tr>
              <td class="label">Database</td>
              <td>{{ diagnostics.services.database.database_name }}</td>
            </tr>
            <tr>
              <td class="label">User</td>
              <td>{{ diagnostics.services.database.user }}</td>
            </tr>
            <tr>
              <td class="label">Size</td>
              <td>{{ diagnostics.services.database.size }}</td>
            </tr>
            <tr>
              <td class="label">Tables</td>
              <td>{{ diagnostics.services.database.public_tables }}</td>
            </tr>
            <tr>
              <td class="label">Latency</td>
              <td>{{ diagnostics.services.database.latency_ms }} ms</td>
            </tr>
            <tr>
              <td class="label">Host</td>
              <td>
                <code>
                  {{ diagnostics.services.database.host }}:{{ diagnostics.services.database.port }}
                </code>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="error-detail">
          <p>{{ diagnostics.services.database.error }}</p>
          <p class="latency">Response time: {{ diagnostics.services.database.latency_ms }} ms</p>
        </div>
      </div>

      <div class="service-card" v-if="diagnostics?.services?.network">
        <div class="card-header">
          <h3>
            <span
              class="dot"
              :class="diagnostics.services.network.status === 'healthy' ? 'green' : 'yellow'"
            ></span>
            Network / DNS
          </h3>
          <span class="badge" :class="diagnostics.services.network.status">
            {{ diagnostics.services.network.status }}
          </span>
        </div>
        <table class="info-table">
          <tbody>
            <tr v-for="(info, name) in diagnostics.services.network.dns_resolution" :key="name">
              <td class="label">{{ name }}</td>
              <td>
                <span class="dot-sm" :class="info.resolved ? 'green' : 'red'"></span>
                {{ info.resolved ? info.ip : 'unresolved' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="service-card parse-methods-card" v-if="diagnostics?.services?.parse_methods">
        <div class="card-header">
          <h3>
            <span
              class="dot"
              :class="statusDotClass(diagnostics.services.parse_methods.status)"
            ></span>
            Parse Methods
          </h3>
          <span class="badge" :class="diagnostics.services.parse_methods.status">
            {{ diagnostics.services.parse_methods.status }}
          </span>
        </div>
        <div class="parse-method-grid">
          <div
            v-for="method in parseMethodCards"
            :key="method.key"
            class="parse-method-card"
            :class="method.toneClass"
          >
            <div class="parse-method-card-header">
              <span class="badge parse-method-badge" :class="method.toneClass">
                {{ method.label }}
              </span>
              <span class="badge" :class="method.status">
                {{ method.status }}
              </span>
            </div>
            <p class="parse-method-availability">
              <span class="dot-sm" :class="statusDotClass(method.status)"></span>
              {{ method.available ? 'Available' : 'Unavailable' }}
            </p>
            <p class="parse-method-message">{{ method.message }}</p>
          </div>
        </div>
      </div>

      <div class="service-card" v-if="diagnostics?.services?.job_board">
        <div class="card-header">
          <h3>
            <span
              class="dot"
              :class="statusDotClass(diagnostics.services.job_board.status)"
            ></span>
            Job Board
          </h3>
          <span class="badge" :class="diagnostics.services.job_board.status">
            {{ diagnostics.services.job_board.status }}
          </span>
        </div>
        <table class="info-table" v-if="!diagnostics.services.job_board.error">
          <tbody>
            <tr>
              <td class="label">Display providers</td>
              <td>{{ (diagnostics.services.job_board.display_enabled_providers || []).join(', ') || 'none' }}</td>
            </tr>
            <tr>
              <td class="label">Active jobs</td>
              <td>{{ diagnostics.services.job_board.counts?.active_jobs ?? 'n/a' }}</td>
            </tr>
            <tr>
              <td class="label">Bad provider URLs</td>
              <td>{{ diagnostics.services.job_board.counts?.bad_provider_urls ?? 'n/a' }}</td>
            </tr>
            <tr>
              <td class="label">Dedup collisions</td>
              <td>{{ diagnostics.services.job_board.dedup?.active_collision_count ?? 'n/a' }}</td>
            </tr>
            <tr>
              <td class="label">/api/jobs/search</td>
              <td>{{ diagnostics.services.job_board.endpoints?.['/api/jobs/search']?.latency_ms ?? 'n/a' }} ms</td>
            </tr>
            <tr>
              <td class="label">/api/jobs/filter-metadata</td>
              <td>{{ diagnostics.services.job_board.endpoints?.['/api/jobs/filter-metadata']?.latency_ms ?? 'n/a' }} ms</td>
            </tr>
            <tr>
              <td class="label">/api/providers/attribution</td>
              <td>{{ diagnostics.services.job_board.endpoints?.['/api/providers/attribution']?.latency_ms ?? 'n/a' }} ms</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="error-detail">
          <p>{{ diagnostics.services.job_board.error }}</p>
        </div>
      </div>

      <div class="service-card">
        <div class="card-header">
          <h3>
            <span class="dot green"></span>
            Frontend
          </h3>
          <span class="badge healthy">healthy</span>
        </div>
        <table class="info-table">
          <tbody>
            <tr>
              <td class="label">Framework</td>
              <td>Vue 3 + Vite</td>
            </tr>
            <tr>
              <td class="label">Server</td>
              <td>Nginx (Alpine)</td>
            </tr>
            <tr>
              <td class="label">User Agent</td>
              <td class="ua-cell">{{ userAgent }}</td>
            </tr>
            <tr>
              <td class="label">Window</td>
              <td>{{ windowSize }}</td>
            </tr>
            <tr>
              <td class="label">Protocol</td>
              <td>{{ protocol }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="diagnostics" class="raw-section">
      <button class="raw-toggle" @click="showRaw = !showRaw">
        {{ showRaw ? 'Hide' : 'Show' }} Raw JSON
      </button>
      <pre v-if="showRaw" class="raw-json">{{ JSON.stringify(diagnostics, null, 2) }}</pre>
    </div>

    <div v-if="error && !diagnostics" class="error-card">
      <h3>Connection Error</h3>
      <p>{{ error }}</p>
      <p class="hint">Make sure you're connected to the VPN and all services are running.</p>
      <pre class="hint-cmd">docker compose ps</pre>
    </div>
  </div>
</template>

<script>
import { authedFetch, getCurrentUser, syncCurrentUser } from '../lib/auth.js'

export default {
  name: 'Status',
  data() {
    return {
      diagnostics: null,
      loading: true,
      error: null,
      accessState: 'ok',
      showRaw: false,
      lastChecked: null,
      userAgent: navigator.userAgent,
      windowSize: `${window.innerWidth} × ${window.innerHeight}`,
      protocol: window.location.protocol,
    }
  },
  async mounted() {
    await this.fetchDiagnostics()
  },
  computed: {
    parseMethodCards() {
      const methods = this.diagnostics?.services?.parse_methods?.methods
      if (!methods) return []

      return ['cloud', 'local', 'rules'].map((key) => {
        const info = methods[key] || {}
        return {
          key,
          label: this.parseMethodLabel(key),
          available: Boolean(info.available),
          status: info.status || (info.available ? 'healthy' : 'degraded'),
          message: info.message || `${this.parseMethodLabel(key)} parsing status is unavailable.`,
          toneClass: this.parseMethodToneClass(key),
        }
      })
    },
  },
  methods: {
    goBack() {
      // Prefer actual history navigation.
      if (window.history.length > 1) {
        this.$router.back()
        return
      }

      const user = getCurrentUser()
      this.$router.push(user ? '/home' : '/login')
    },
    parseMethodLabel(key) {
      if (key === 'cloud') return 'Cloud'
      if (key === 'rules') return 'Rules'
      return 'Local'
    },
    parseMethodToneClass(key) {
      if (key === 'cloud') return 'method-cloud'
      if (key === 'rules') return 'method-rules'
      return 'method-local'
    },
    statusDotClass(status) {
      if (status === 'healthy') return 'green'
      if (status === 'degraded') return 'yellow'
      return 'red'
    },
    async fetchDiagnostics() {
      this.loading = true
      this.error = null
      this.accessState = 'ok'
      try {
        const user = await syncCurrentUser({ force: true })
        if (!user) {
          this.diagnostics = null
          this.lastChecked = null
          this.accessState = 'signin-required'
          return
        }

        const res = await authedFetch('/api/diagnostics')
        if (res.status === 403) {
          this.diagnostics = null
          this.lastChecked = null
          this.accessState = 'admin-required'
          return
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        this.diagnostics = await res.json()
        this.lastChecked = new Date().toLocaleTimeString()
      } catch (err) {
        const message = err?.message ?? String(err)
        if (message === 'Not authenticated' || message === 'Session expired') {
          this.accessState = 'signin-required'
          this.error = null
          this.diagnostics = null
          this.lastChecked = null
        } else {
          this.error = message
        }
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped src="./css/StatusPage.css"></style>
