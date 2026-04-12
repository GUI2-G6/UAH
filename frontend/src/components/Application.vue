<template>
    <h2>{{ application.company }}</h2>
    <h3>{{ application.role }}</h3>
    <h3>Sent {{ application.dateSent }}</h3>

    <h3>Status:</h3>
    <ProgressBar 
        :value="application.statusStep" 
        :max="application.maxStep" 
    />

    <h3 v-if="application.statusText">
        {{ application.statusText }}
    </h3>

    <label>
        <span>No response?</span>
        <input type="checkbox" v-model="localNoResponse" />
    </label>
</template>

<script>
import ProgressBar from "./ProgressBar.vue"

export default {
  name: "Application",
  components: {
    ProgressBar
  },

  props: {
    application: Object
  },

  data() {
    return {
      localNoResponse: this.application.noResponse || false
    }
  }
}
</script>

<style scoped></style>