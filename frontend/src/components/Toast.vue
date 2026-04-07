<template>
  <transition name="fade">
    <div v-if="toastStore.visible" :class="['toast', toastStore.type]">
      {{ toastStore.message }}
    </div>
  </transition>
</template>

<script>
import { toastStore } from '@/services/toastService.js';

export default {
  setup() {
    return { toastStore };
  }
};
</script>

<style>
.toast {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  top: auto;
  left: auto;
  padding: 1rem;
  border-radius: 4px;
  color: white !important;
  z-index: 9999;
}
.toast.success { background-color: #4CAF50; }
.toast.error { background-color: #F44336; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>