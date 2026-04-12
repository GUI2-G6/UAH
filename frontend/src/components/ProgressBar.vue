<template>
  <div class="progress">
    <div 
      class="progress-fill"
      :style="{ width: percent + '%' }"
    ></div>
  </div>
</template>

<script>
export default {
  name: "ProgressBar",
  props: {
    value: Number,
    max: {
      type: Number,
      default: 100
    }
  },
  computed: {
    percent() {
      return Math.min((this.value / this.max) * 100, 100)
    }
  }
}
</script>

<style scoped>
.progress {
  width: 100%;
  height: 16px;
  background: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3f62ec;
  transition: width 0.3s ease;
}
</style>