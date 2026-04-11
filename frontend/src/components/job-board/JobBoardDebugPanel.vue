<template>
  <section class="debug-panel">
    <div class="debug-panel-header">
      <div>
        <p class="debug-eyebrow">Dev only</p>
        <h3>Search diagnostics</h3>
      </div>
      <span class="debug-badge">Internal</span>
    </div>

    <div class="debug-grid">
      <div class="debug-item">
        <span class="debug-label">Source pages</span>
        <strong>{{ Number(diagnostics.sourcePagesScanned || 0) }}</strong>
      </div>
      <div class="debug-item">
        <span class="debug-label">Filtered out</span>
        <strong>{{ Number(diagnostics.filteredOutCount || 0) }}</strong>
      </div>
      <div class="debug-item">
        <span class="debug-label">Invalid links</span>
        <strong>{{ Number(diagnostics.droppedInvalidUrlCount || 0) }}</strong>
      </div>
      <div class="debug-item">
        <span class="debug-label">Location fallback</span>
        <strong>{{ diagnostics.locationRelaxedFallback === true ? 'Used' : 'No' }}</strong>
      </div>
    </div>

    <p v-if="pretrimLocationNotice" class="debug-note">{{ pretrimLocationNotice }}</p>
    <p v-if="filterMetadataVersion || filterMetadataHash" class="debug-note">
      Filter metadata: {{ filterMetadataVersion || 'unknown' }}<span v-if="filterMetadataHash"> · {{ filterMetadataHash }}</span>
    </p>
  </section>
</template>

<script>
export default {
  name: 'JobBoardDebugPanel',
  props: {
    diagnostics: {
      type: Object,
      default: () => ({}),
    },
    pretrimLocationNotice: {
      type: String,
      default: '',
    },
    filterMetadataVersion: {
      type: String,
      default: '',
    },
    filterMetadataHash: {
      type: String,
      default: '',
    },
  },
}
</script>

<style scoped>
.debug-panel {
  margin: 14px 16px 0;
  border: 1px dashed rgba(15, 118, 110, 0.45);
  border-radius: 18px;
  background: rgba(240, 253, 250, 0.78);
  padding: 16px;
}

.debug-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.debug-eyebrow {
  margin: 0 0 4px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f766e;
}

h3 {
  margin: 0;
  color: #0f172a;
}

.debug-badge {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.76rem;
  font-weight: 700;
  color: #0f766e;
  border: 1px solid rgba(15, 118, 110, 0.35);
}

.debug-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.debug-item {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.72);
}

.debug-label {
  display: block;
  font-size: 0.8rem;
  color: #475569;
  margin-bottom: 4px;
}

.debug-note {
  margin: 10px 0 0;
  color: #475569;
  font-size: 0.88rem;
}

@media (max-width: 700px) {
  .debug-panel {
    margin: 12px 12px 0;
    padding: 14px;
  }
}
</style>
