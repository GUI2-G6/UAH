<template>
  <div class="job-board-pagination">
    <button type="button" @click="$emit('previous')" :disabled="page <= 1 || loading">Previous</button>
    <button
      type="button"
      v-for="pageNumber in visiblePages"
      :key="`${idPrefix}-${pageNumber}`"
      :class="{ active: pageNumber === page }"
      :disabled="loading"
      @click="$emit('select-page', pageNumber)"
    >
      {{ pageNumber }}
    </button>
    <span class="pagination-total">of {{ totalPages }}{{ totalsAreEstimated ? ' est.' : '' }}</span>
    <form class="page-jump-form" @submit.prevent="submitPageJump">
      <label class="page-jump-label" :for="inputId">Page</label>
      <input
        :id="inputId"
        v-model.trim="pageInput"
        type="number"
        inputmode="numeric"
        min="1"
        :max="Math.max(1, totalPages)"
        :disabled="loading"
      />
      <button type="submit" :disabled="loading">Go</button>
    </form>
    <button type="button" @click="$emit('next')" :disabled="!hasNextPage || loading">Next</button>
  </div>
</template>

<script>
export default {
  name: "JobBoardPagination",
  props: {
    page: {
      type: Number,
      default: 1,
    },
    totalPages: {
      type: Number,
      default: 1,
    },
    visiblePages: {
      type: Array,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
    hasNextPage: {
      type: Boolean,
      default: false,
    },
    totalsAreEstimated: {
      type: Boolean,
      default: false,
    },
    idPrefix: {
      type: String,
      default: "jobs",
    },
  },
  emits: ["previous", "next", "select-page"],
  data() {
    return {
      pageInput: String(this.page || 1),
    }
  },
  computed: {
    inputId() {
      return `${this.idPrefix}-page-jump`
    },
  },
  watch: {
    page: {
      immediate: true,
      handler(nextValue) {
        this.pageInput = String(nextValue || 1)
      },
    },
  },
  methods: {
    submitPageJump() {
      const parsed = Number.parseInt(this.pageInput, 10)
      if (!Number.isFinite(parsed)) {
        this.pageInput = String(this.page || 1)
        return
      }
      const clamped = Math.max(1, Math.min(Math.max(1, this.totalPages || 1), parsed))
      this.pageInput = String(clamped)
      this.$emit("select-page", clamped)
    },
  },
}
</script>

<style scoped>
.job-board-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px;
}

.job-board-pagination button,
.page-jump-form input {
  border: 1px solid #c9cfda;
  border-radius: 10px;
  min-height: 40px;
  background: #ffffff;
  color: #1f2937;
}

.job-board-pagination button {
  padding: 8px 14px;
  cursor: pointer;
}

.job-board-pagination button.active {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
  color: #ffffff;
}

.job-board-pagination button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.pagination-total {
  color: #334155;
  font-weight: 600;
}

.page-jump-form {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.page-jump-label {
  font-size: 0.84rem;
  color: #475569;
  font-weight: 600;
}

.page-jump-form input {
  width: 80px;
  padding: 8px 10px;
}

@media (max-width: 640px) {
  .job-board-pagination,
  .page-jump-form {
    width: 100%;
  }

  .page-jump-form input,
  .page-jump-form button {
    flex: 1;
  }
}
</style>
