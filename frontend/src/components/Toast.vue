<template>
    <transition name="fade">
        <div v-if="visible" :class="['toast', type]">
        {{ message }}
        </div>
    </transition>
</template>

<script>
export default {
  props: {
    message: { type: String, required: true },
    type: { type: String, default: 'success' } // 'success' | 'error'
  },
  data() {
    return { visible: true };
  },
  mounted() {
    setTimeout(() => this.visible = false, 3000); // auto-hide after 3s
  }
};
</script>