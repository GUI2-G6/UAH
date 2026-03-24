<template>
  <div class="secret-input">
    <input
      :type="computedType"
      :value="modelValue"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      :disabled="disabled"
      :class="inputClass"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <button
      type="button"
      class="toggle"
      :disabled="disabled"
      :aria-pressed="revealed ? 'true' : 'false'"
      @click="toggle"
    >
      {{ revealed ? 'Hide' : 'Show' }}
    </button>
  </div>
</template>

<script>
export default {
  name: 'SecretInput',
  props: {
    modelValue: {
      type: String,
      default: '',
    },
    placeholder: {
      type: String,
      default: '',
    },
    autocomplete: {
      type: String,
      default: 'off',
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    inputClass: {
      type: [String, Object, Array],
      default: '',
    },
    hiddenType: {
      type: String,
      default: 'password',
    },
  },
  emits: ['update:modelValue'],
  data() {
    return {
      revealed: false,
    }
  },
  computed: {
    computedType() {
      return this.revealed ? 'text' : this.hiddenType
    },
  },
  methods: {
    toggle() {
      this.revealed = !this.revealed
    },
  },
}
</script>

<style scoped>
.secret-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.secret-input input {
  flex: 1;
}

.toggle {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  background: #f0f4f8;
  color: #1a1a2e;
  cursor: pointer;
  white-space: nowrap;
}

.toggle:disabled {
  opacity: 0.7;
  cursor: default;
}
</style>
