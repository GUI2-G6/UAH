<template>
  <div class="debug-overlay" role="dialog" aria-modal="true" aria-label="Debug diagnostic view" @click="close">
    <div class="debug-dialog" v-draggable-modal="{ handle: '.debug-header' }" @click.stop>
      <div class="debug-header drag-handle">
        <h2>Debug Diagnostic View</h2>
        <button type="button" class="debug-close" @click="close">Close</button>
      </div>

      <div class="debug-body">
        <section class="debug-section">
          <h3>Route</h3>
          <pre>{{ formattedRoute }}</pre>
        </section>

        <section class="debug-section">
          <h3>Page Diagnostics</h3>
          <pre>{{ formattedPageDiagnostics }}</pre>
        </section>

        <section class="debug-section">
          <h3>Recent Requests</h3>
          <pre>{{ formattedRequests }}</pre>
        </section>
      </div>

      <div class="debug-actions">
        <button type="button" @click="copySnapshot">Copy Snapshot</button>
        <button type="button" @click="openDiagnosticsConsole">Open Job Board Console</button>
        <button type="button" class="debug-close" @click="close">Close</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "DebugDiagnosticModal",
  props: {
    snapshot: {
      type: Object,
      default: () => ({}),
    },
  },
  emits: ["close"],
  computed: {
    formattedRoute() {
      const route = this.snapshot?.route || {}
      const env = this.snapshot?.environment || {}
      return JSON.stringify(
        {
          at: this.snapshot?.generatedAt || "",
          route,
          environment: {
            location: env.location || "",
          },
        },
        null,
        2,
      )
    },
    formattedPageDiagnostics() {
      return JSON.stringify(this.snapshot?.pageDiagnostics || {}, null, 2)
    },
    formattedRequests() {
      const requests = this.snapshot?.recentRequests || []
      return JSON.stringify(requests.slice(0, 12), null, 2)
    },
  },
  methods: {
    close() {
      this.$emit("close")
    },
    async copySnapshot() {
      try {
        await navigator.clipboard.writeText(JSON.stringify(this.snapshot || {}, null, 2))
      } catch {
        // Clipboard support is optional.
      }
    },
    openDiagnosticsConsole() {
      this.$router.push('/dev')
      this.close()
    },
  },
}
</script>

<style scoped>
.debug-overlay {
  position: fixed;
  inset: 0;
  z-index: 10010;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(2, 6, 23, 0.5);
}

.debug-dialog {
  width: min(900px, 96vw);
  max-height: 86vh;
  background: #ffffff;
  border: 1px solid #dbe1e7;
  border-radius: 12px;
  box-shadow: 0 20px 38px rgba(15, 23, 42, 0.2);
  display: flex;
  flex-direction: column;
}

.debug-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid #e7eaee;
  cursor: grab;
}

.debug-header h2 {
  margin: 0;
  font-size: 1.04rem;
  color: #111827;
}

.debug-body {
  padding: 12px 14px;
  overflow: auto;
  display: grid;
  gap: 10px;
}

.debug-section {
  border: 1px solid #e7eaee;
  border-radius: 10px;
  background: #fafbfc;
  padding: 10px;
}

.debug-section h3 {
  margin: 0 0 8px;
  font-size: 0.95rem;
  color: #1f2937;
}

.debug-section pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.8rem;
  color: #0f172a;
}

.debug-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 0 14px 12px;
}

.debug-actions button,
.debug-close {
  border: 1px solid #c9cfda;
  border-radius: 8px;
  padding: 7px 12px;
  cursor: pointer;
  background: #f8fafc;
  color: #1f2937;
}
</style>
