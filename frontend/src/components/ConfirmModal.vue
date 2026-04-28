<template>
  <div class="confirm-overlay" role="dialog" aria-modal="true" :aria-label="title || 'Confirm'">
    <div class="confirm-dialog" v-draggable-modal="{ handle: '.confirm-head' }" @click.stop>
      <div class="confirm-head drag-handle">
        <h2 class="confirm-title" v-if="title">{{ title }}</h2>
      </div>
      <p class="confirm-message">{{ message }}</p>

      <div class="confirm-actions">
        <button
          type="button"
          class="confirm-btn cancel"
          :disabled="busy"
          @click="$emit('cancel')"
        >
          {{ cancelText }}
        </button>
        <button
          type="button"
          class="confirm-btn danger"
          :disabled="busy"
          @click="$emit('confirm')"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConfirmModal',
  props: {
    title: {
      type: String,
      default: '',
    },
    message: {
      type: String,
      required: true,
    },
    cancelText: {
      type: String,
      default: 'No, go back',
    },
    confirmText: {
      type: String,
      default: 'Yes, confirm',
    },
    busy: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['confirm', 'cancel'],
  mounted() {
    this._onKeyDown = (e) => {
      if (e.key === 'Escape') {
        this.$emit('cancel')
      }
    }
    window.addEventListener('keydown', this._onKeyDown)
  },
  beforeUnmount() {
    if (this._onKeyDown) {
      window.removeEventListener('keydown', this._onKeyDown)
    }
  },
}
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.45);
}

.confirm-dialog {
  width: min(460px, 92vw);
  background: var(--color-surface);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 22px 20px;
  text-align: center;
}

.confirm-head {
  cursor: grab;
}

.confirm-title {
  margin: 0 0 10px;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.confirm-message {
  margin: 0 0 16px;
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.confirm-btn {
  padding: 12px 14px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 600;
}

.confirm-btn:disabled {
  opacity: 0.7;
  cursor: default;
}

.confirm-btn.cancel {
  background: var(--color-surface);
  color: var(--color-text-primary);
  border: 1px solid var(--border-color);
}

.confirm-btn.danger {
  background: var(--color-surface);
  color: var(--color-text-primary);
  border: 1px solid var(--border-color);
}

.confirm-btn.danger:hover:enabled {
  background: #ef4444;
  border-color: #ef4444;
  color: #ffffff;
}

:global(html[data-theme="dark"]) .confirm-dialog {
  background: var(--color-surface);
  border: 1px solid var(--border-color);
  box-shadow: 0 20px 40px rgba(2, 6, 23, 0.55);
}

:global(html[data-theme="dark"]) .confirm-title {
  color: var(--color-text-primary);
}

:global(html[data-theme="dark"]) .confirm-message {
  color: var(--color-text-secondary);
}

:global(html[data-theme="dark"]) .confirm-btn.cancel {
  background: var(--color-surface);
  border-color: var(--border-color);
  color: var(--color-text-primary);
}

:global(html[data-theme="dark"]) .confirm-btn.cancel:hover:enabled {
  background: var(--color-surface-hover);
}

:global(html[data-theme="dark"]) .confirm-btn.danger {
  background: var(--color-surface);
  border-color: var(--border-color);
  color: var(--color-text-primary);
}

:global(html[data-theme="dark"]) .confirm-btn.danger:hover:enabled {
  background: rgba(239, 68, 68, 0.24);
  border-color: rgba(248, 113, 113, 0.82);
  color: #fee2e2;
}
</style>
