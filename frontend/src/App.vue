<template>
  <div id="uah-app">
    <Burger v-if="showBurger" />
    <div id="main-content">
      <div id="current-page">
        <router-view />
      </div>
      <Footer @open-debug-view="openDebugView" />
    </div>
    <DebugDiagnosticModal v-if="debugViewOpen" :snapshot="debugSnapshot" @close="closeDebugView" />
  </div>
</template>

<script>
  import Burger from "./components/Burger.vue";
  import Footer from "./components/Footer.vue";
  import DebugDiagnosticModal from "./components/DebugDiagnosticModal.vue";
  import { setDebugRouteSnapshot, subscribeDebugState } from "./lib/debugDiagnostics";

  export default {
    name: "App",
    components: {
      Burger,
      Footer,
      DebugDiagnosticModal
    },
    data() {
      return {
        debugViewOpen: false,
        debugSnapshot: {},
        debugUnsubscribe: null,
      }
    },
    watch: {
      $route: {
        immediate: true,
        handler(route) {
          setDebugRouteSnapshot(route)
        },
      },
    },
    computed: {
      showBurger() {
        return !['/login', '/register', '/status', '/forgot-password', '/reset-password'].includes(this.$route.path)
      }
    },
    mounted() {
      this.debugUnsubscribe = subscribeDebugState((snapshot) => {
        this.debugSnapshot = snapshot
      })
    },
    beforeUnmount() {
      if (typeof this.debugUnsubscribe === "function") {
        this.debugUnsubscribe()
      }
    },
    methods: {
      openDebugView() {
        this.debugViewOpen = true
      },
      closeDebugView() {
        this.debugViewOpen = false
      },
    }
  }
</script>

<style src="./App.css"></style>

