<template>
  <div>
    <button @click="showError('Test successful')">Show Error Toast</button>
  </div>
</template>

<script>
import { showToast } from './toastService.js';

export default {
  name: 'Test',
  methods: {
    showError(message) {
      showToast(message, 'error');
    },
    showSuccess(message) {
      showToast(message, 'success');
    }
  }
};
</script>