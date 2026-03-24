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
  import Navbar from "./components/Navbar.vue";
  import Burger from "./components/Burger.vue";
  import Footer from "./components/Footer.vue";
  import Home from "./views/Home.vue";

  export default {
    name: "App",
    components: {
      Navbar,
      Burger,
      Footer,
      Home
    },
    computed: {
      showBurger() {
        return !['/login', '/register', '/status'].includes(this.$route.path)
      }
    }
  }
</script>

<style src="./App.css"></style>

