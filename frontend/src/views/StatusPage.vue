<template>
  <div class="status-page">
    <!-- Header -->
    <div class="page-header">
      <h2>System Status</h2>
      <div class="header-actions">
        <span class="last-checked" v-if="lastChecked">
          Last checked: {{ lastChecked }}
        </span>
        <button class="refresh-btn" @click="fetchDiagnostics" :disabled="loading">
          {{ loading ? 'Checking...' : 'Refresh' }}
        </button>
      </div>
    </div>

    <!-- Overall Status Banner -->
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

    <!-- Loading state -->
    <div v-if="loading && !diagnostics" class="loading-state">
      <div class="spinner"></div>
      <p>Running diagnostics...</p>
    </div>

    <!-- Service Cards -->
    <div v-if="diagnostics" class="service-grid">

      <!-- Backend Card -->
      <div class="service-card" v-if="diagnostics.services.backend">
        <div class="card-header">
          <h3>
            <span class="dot" :class="diagnostics.services.backend.status === 'healthy' ? 'green' : 'red'"></span>
            Backend
          </h3>
          <span class="badge" :class="diagnostics.services.backend.status">
            {{ diagnostics.services.backend.status }}
          </span>
        </div>
        <table class="info-table">
          <tr>
            <td class="label">Service</td>
            <td>{{ diagnostics.services.backend.name }} v{{ diagnostics.services.backend.version }}</td>
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
        </table>
      </div>

      <!-- Database Card -->
      <div class="service-card" v-if="diagnostics.services.database">
        <div class="card-header">
          <h3>
            <span class="dot" :class="diagnostics.services.database.status === 'healthy' ? 'green' : 'red'"></span>
            Database
          </h3>
          <span class="badge" :class="diagnostics.services.database.status">
            {{ diagnostics.services.database.status }}
          </span>
        </div>
        <table class="info-table" v-if="diagnostics.services.database.status === 'healthy'">
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
            <td><code>{{ diagnostics.services.database.host }}:{{ diagnostics.services.database.port }}</code></td>
          </tr>
        </table>
        <div v-else class="error-detail">
          <p>{{ diagnostics.services.database.error }}</p>
          <p class="latency">Response time: {{ diagnostics.services.database.latency_ms }} ms</p>
        </div>
      </div>

      <!-- Network Card -->
      <div class="service-card" v-if="diagnostics.services.network">
        <div class="card-header">
          <h3>
            <span class="dot" :class="diagnostics.services.network.status === 'healthy' ? 'green' : 'yellow'"></span>
            Network / DNS
          </h3>
          <span class="badge" :class="diagnostics.services.network.status">
            {{ diagnostics.services.network.status }}
          </span>
        </div>
        <table class="info-table">
          <tr v-for="(info, name) in diagnostics.services.network.dns_resolution" :key="name">
            <td class="label">{{ name }}</td>
            <td>
              <span class="dot-sm" :class="info.resolved ? 'green' : 'red'"></span>
              {{ info.resolved ? info.ip : 'unresolved' }}
            </td>
          </tr>
        </table>
      </div>

      <!-- Frontend Card (client-side info) -->
      <div class="service-card">
        <div class="card-header">
          <h3>
            <span class="dot green"></span>
            Frontend
          </h3>
          <span class="badge healthy">healthy</span>
        </div>
        <table class="info-table">
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
        </table>
      </div>

    </div>

    <!-- Raw JSON toggle -->
    <div v-if="diagnostics" class="raw-section">
      <button class="raw-toggle" @click="showRaw = !showRaw">
        {{ showRaw ? 'Hide' : 'Show' }} Raw JSON
      </button>
      <pre v-if="showRaw" class="raw-json">{{ JSON.stringify(diagnostics, null, 2) }}</pre>
    </div>

    <!-- Error detail -->
    <div v-if="error && !diagnostics" class="error-card">
      <h3>Connection Error</h3>
      <p>{{ error }}</p>
      <p class="hint">Make sure you're connected to the VPN and all services are running.</p>
      <pre class="hint-cmd">docker compose ps</pre>
    </div>
  </div>
</template>

<script>
export default {
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
    async fetchDiagnostics() {
      this.loading = true
      this.error = null
      try {
        const res = await fetch('/api/diagnostics')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        this.diagnostics = await res.json()
        this.lastChecked = new Date().toLocaleTimeString()
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped>
.status-page {
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-header h2 {
  font-size: 1.4rem;
  color: #e1e4e8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.last-checked {
  font-size: 0.8rem;
  color: #8b949e;
}

.refresh-btn {
  background: #21262d;
  color: #58a6ff;
  border: 1px solid #30363d;
  padding: 6px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.15s;
}

.refresh-btn:hover:not(:disabled) {
  background: #30363d;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Overall banner */
.overall-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  border-radius: 8px;
  margin-bottom: 24px;
  font-size: 1.05rem;
  font-weight: 500;
}

.overall-banner.healthy {
  background: rgba(63, 185, 80, 0.1);
  border: 1px solid rgba(63, 185, 80, 0.3);
  color: #3fb950;
}

.overall-banner.degraded {
  background: rgba(210, 153, 34, 0.1);
  border: 1px solid rgba(210, 153, 34, 0.3);
  color: #d29922;
}

.overall-banner.unhealthy {
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid rgba(248, 81, 73, 0.3);
  color: #f85149;
}

.overall-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.overall-dot.healthy { background: #3fb950; }
.overall-dot.degraded { background: #d29922; }
.overall-dot.unhealthy { background: #f85149; }

/* Loading */
.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #8b949e;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #30363d;
  border-top-color: #58a6ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Service grid */
.service-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.service-card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 8px;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-header h3 {
  font-size: 1rem;
  color: #e1e4e8;
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge {
  font-size: 0.75rem;
  padding: 2px 10px;
  border-radius: 12px;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.badge.healthy {
  background: rgba(63, 185, 80, 0.15);
  color: #3fb950;
}

.badge.unhealthy {
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
}

.badge.degraded {
  background: rgba(210, 153, 34, 0.15);
  color: #d29922;
}

/* Info table */
.info-table {
  width: 100%;
  border-collapse: collapse;
}

.info-table tr {
  border-bottom: 1px solid #21262d;
}

.info-table tr:last-child {
  border-bottom: none;
}

.info-table td {
  padding: 6px 0;
  font-size: 0.85rem;
  color: #c9d1d9;
  vertical-align: top;
}

.info-table .label {
  color: #8b949e;
  width: 100px;
  font-weight: 500;
}

.info-table code {
  background: #0d1117;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #79c0ff;
}

.ua-cell {
  word-break: break-all;
  font-size: 0.78rem !important;
}

/* Dots */
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.dot-sm {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
}

.dot.green, .dot-sm.green { background: #3fb950; }
.dot.red, .dot-sm.red { background: #f85149; }
.dot.yellow, .dot-sm.yellow { background: #d29922; }

/* Error in card */
.error-detail {
  color: #f85149;
  font-size: 0.85rem;
}

.error-detail .latency {
  color: #8b949e;
  margin-top: 8px;
  font-size: 0.8rem;
}

/* Raw JSON */
.raw-section {
  margin-bottom: 24px;
}

.raw-toggle {
  background: none;
  border: 1px solid #30363d;
  color: #8b949e;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  margin-bottom: 8px;
}

.raw-toggle:hover {
  color: #c9d1d9;
  border-color: #484f58;
}

.raw-json {
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 16px;
  font-size: 0.78rem;
  color: #79c0ff;
  overflow-x: auto;
  margin-top: 8px;
}

/* Error card */
.error-card {
  background: rgba(248, 81, 73, 0.08);
  border: 1px solid rgba(248, 81, 73, 0.3);
  border-radius: 8px;
  padding: 24px;
  text-align: center;
}

.error-card h3 {
  color: #f85149;
  margin-bottom: 8px;
}

.error-card p {
  color: #c9d1d9;
  font-size: 0.9rem;
}

.error-card .hint {
  color: #8b949e;
  margin-top: 16px;
  font-size: 0.85rem;
}

.error-card .hint-cmd {
  background: #0d1117;
  color: #79c0ff;
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  margin-top: 8px;
  font-size: 0.85rem;
}
</style>
