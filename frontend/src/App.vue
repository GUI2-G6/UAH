<template>
  <div id="uah-app">
    <Burger v-if="showBurger" />
    <div id="main-content">
      <div id="current-page">
        <router-view />
      </div>
      <Footer />
    </div>
  </div>
</template>

<script>
  import Burger from "./components/Burger.vue";
  import Footer from "./components/Footer.vue";

  export default {
    name: "App",
    components: {
      Burger,
      Footer
    },
    computed: {
      showBurger() {
        return !['/login', '/register', '/status', '/forgot-password', '/reset-password'].includes(this.$route.path)
      }
    }
  }
</script>

<style src="./App.css"></style>

