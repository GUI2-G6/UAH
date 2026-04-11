<template>
  <div class="secret-input">
    <input
      :id="id"
      :name="name"
      :type="computedType"
      :value="modelValue"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      :inputmode="inputmode"
      :autocapitalize="autocapitalize"
      :autocorrect="autocorrect"
      :spellcheck="spellcheck"
      :disabled="disabled"
      :class="[inputClass, { 'secret-input-default': !inputClass, 'secret-input-auth': useAuthStyles }]"
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
    id: {
      type: String,
      default: '',
    },
    name: {
      type: String,
      default: '',
    },
    autocomplete: {
      type: String,
      default: 'off',
    },
    inputmode: {
      type: String,
      default: 'text',
    },
    autocapitalize: {
      type: String,
      default: 'off',
    },
    autocorrect: {
      type: String,
      default: 'off',
    },
    spellcheck: {
      type: [Boolean, String],
      default: false,
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
    useAuthStyles() {
      const cls = this.inputClass
      if (!cls) return false
      if (typeof cls === 'string') return cls.split(/\s+/).includes('email-input')
      if (Array.isArray(cls)) return cls.some((c) => typeof c === 'string' && c.split(/\s+/).includes('email-input'))
      // Object form: { 'email-input': true }
      if (typeof cls === 'object') return !!cls['email-input']
      return false
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
  align-items: stretch;
  gap: 8px;
}

.secret-input input {
  flex: 1;
  min-width: 0;
}

.secret-input-default {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  background: #ffffff;
  outline: none;
}

/* Auth pages use scoped CSS, so their `.email-input` styles don't reach this child component.
   When the parent passes `inputClass="email-input"`, apply the same look locally. */
.secret-input-auth {
  width: 100%;
  padding: 14px 16px;
  border: none;
  border-radius: 8px;
  background: #f0f4f8;
  font-size: 0.92rem;
  color: #1a1a2e;
  outline: none;
}

.toggle {
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  background: #f0f4f8;
  color: #1a1a2e;
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.toggle:disabled {
  opacity: 0.7;
  cursor: default;
}
</style>
