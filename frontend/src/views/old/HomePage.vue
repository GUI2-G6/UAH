<template>
  <div>
    <section class="status-card">
      <h2>Backend Connection</h2>
      <div v-if="loading" class="status loading">Connecting...</div>
      <div v-else-if="error" class="status error">
        <span class="dot red"></span>
        Disconnected — {{ error }}
      </div>
      <div v-else class="status ok">
        <span class="dot green"></span>
        Connected — {{ apiStatus.message }} ({{ apiStatus.environment }})
      </div>
    </section>
  </div>
</template>

<script>
export default {
  data() {
    return {
      apiStatus: null,
      loading: true,
      error: null,
    }
  },
  async mounted() {
    try {
      const res = await fetch('/api/status')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      this.apiStatus = await res.json()
    } catch (err) {
      this.error = err.message
    } finally {
      this.loading = false
    }
  },
}
</script>
