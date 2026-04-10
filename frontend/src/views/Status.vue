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
    <div v-else-if="error" class="overall-banner unhealthy">
      <span class="overall-dot unhealthy"></span>
      <span class="overall-text">Unable to reach backend</span>
    </div>

    <div v-if="loading && !diagnostics" class="loading-state">
      <div class="spinner"></div>
      <p>Running diagnostics...</p>
    </div>

    <div v-if="diagnostics" class="service-grid">
      <div class="service-card" v-if="diagnostics.services.backend">
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

      <div class="service-card" v-if="diagnostics.services.database">
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

      <div class="service-card" v-if="diagnostics.services.network">
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
import { getAccessToken } from '../lib/auth.js'

export default {
  name: 'Status',
  data() {
    return {
      diagnostics: null,
      loading: true,
      error: null,
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
  methods: {
    goBack() {
      // Prefer actual history navigation.
      if (window.history.length > 1) {
        this.$router.back()
        return
      }

      const token = getAccessToken()
      this.$router.push(token ? '/home' : '/login')
    },
    async fetchDiagnostics() {
      this.loading = true
      this.error = null
      try {
        const res = await fetch('/api/diagnostics')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        this.diagnostics = await res.json()
        this.lastChecked = new Date().toLocaleTimeString()
      } catch (err) {
        this.error = err?.message ?? String(err)
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped src="./css/StatusPage.css"></style>
