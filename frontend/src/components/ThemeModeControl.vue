<template>
  <div
    :id="id"
    class="uah-theme-segment"
    :class="{ 'uah-theme-segment--compact': compact }"
    role="group"
    :aria-label="groupLabel"
  >
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      class="uah-theme-segment__btn"
      :class="{ 'is-active': preference === opt.value }"
      :aria-pressed="preference === opt.value ? 'true' : 'false'"
      @click="choose(opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<script>
import {
  getStoredPreference,
  setPreferenceAndApply,
} from '@shared/js/themePreference.js'

const OPTIONS = [
  { value: 'system', label: 'Auto' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
]

export default {
  name: 'ThemeModeControl',
  props: {
    compact: {
      type: Boolean,
      default: false,
    },
    groupLabel: {
      type: String,
      default: 'Color theme',
    },
    id: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      preference: 'system',
      options: OPTIONS,
      _unsub: null,
    }
  },
  created() {
    this.preference = getStoredPreference() ?? 'system'
  },
  mounted() {
    this._unsub = () => {
      this.preference = getStoredPreference() ?? 'system'
    }
    window.addEventListener('uah-theme-changed', this._unsub)
    window.addEventListener('storage', this._unsub)
  },
  beforeUnmount() {
    if (this._unsub) {
      window.removeEventListener('uah-theme-changed', this._unsub)
      window.removeEventListener('storage', this._unsub)
    }
  },
  methods: {
    choose(value) {
      setPreferenceAndApply(value)
      this.preference = value
    },
  },
}
</script>
