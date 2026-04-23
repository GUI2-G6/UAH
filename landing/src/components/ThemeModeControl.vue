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

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import {
  getStoredPreference,
  setPreferenceAndApply,
} from '@shared/js/themePreference.js'

const OPTIONS = [
  { value: 'system', label: 'Auto' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
]

defineProps({
  id: {
    type: String,
    default: '',
  },
  compact: {
    type: Boolean,
    default: false,
  },
  groupLabel: {
    type: String,
    default: 'Color theme',
  },
})

const preference = ref('system')
const options = OPTIONS

function sync() {
  preference.value = getStoredPreference() ?? 'system'
}

function choose(value) {
  setPreferenceAndApply(value)
  preference.value = value
}

onMounted(() => {
  sync()
  window.addEventListener('uah-theme-changed', sync)
  window.addEventListener('storage', sync)
})

onUnmounted(() => {
  window.removeEventListener('uah-theme-changed', sync)
  window.removeEventListener('storage', sync)
})
</script>
