<template>
  <div id="uah-app">
    <Burger v-if="showBurger" />
    <div id="main-content">
      <div id="current-page">
        <!--<Test />-->
        <router-view />
      </div>
      <Footer :show-debug-tools="showDebugTools" @open-debug-view="openDebugView" />
    </div>
    <Toast />
    <DebugDiagnosticModal v-if="showDebugTools && debugViewOpen" :snapshot="debugSnapshot" @close="closeDebugView" />
  </div>
</template>

<script>
  import Test from "./components/Test.vue";
  import Toast from "./components/Toast.vue";
  import Burger from "./components/Burger.vue";
  import Footer from "./components/Footer.vue";
  import DebugDiagnosticModal from "./components/DebugDiagnosticModal.vue";
  import { setDebugRouteSnapshot, subscribeDebugState } from "./lib/debugDiagnostics";
  import { subscribeDebugTools } from "./lib/debugTools";

  export default {
    name: "App",
    components: {
      Burger,
      Footer,
      Test,
      Toast,
      DebugDiagnosticModal
    },
    data() {
      return {
        debugViewOpen: false,
        debugSnapshot: {},
        debugUnsubscribe: null,
        debugToolsUnsubscribe: null,
        showDebugTools: false,
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
        return !['/login', '/register', '/status', '/forgot-password', '/reset-password', '/oauth-callback'].includes(this.$route.path)
      }
    },
    mounted() {
      this.debugUnsubscribe = subscribeDebugState((snapshot) => {
        this.debugSnapshot = snapshot
      })
      this.debugToolsUnsubscribe = subscribeDebugTools((state) => {
        this.showDebugTools = state.showDebugTools === true
        if (!this.showDebugTools) {
          this.debugViewOpen = false
          if (this.$route?.meta?.debugOnly) {
            this.$router.replace('/home')
          }
        }
      })
    },
    beforeUnmount() {
      if (typeof this.debugUnsubscribe === "function") {
        this.debugUnsubscribe()
      }
      if (typeof this.debugToolsUnsubscribe === "function") {
        this.debugToolsUnsubscribe()
      }
    },
    methods: {
      openDebugView() {
        if (!this.showDebugTools) return
        this.debugViewOpen = true
      },
      closeDebugView() {
        this.debugViewOpen = false
      },
    }
  }
</script>

<style src="./App.css"></style>

