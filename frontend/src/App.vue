<template>
  <div id="uah-app">
    <Burger />
    <div id="current-page">
      <router-view />
    </div>
  </div>
</template>

<script>
  import Navbar from "./components/Navbar.vue";
  import Burger from "./components/Burger.vue";
  import Home from "./views/Home.vue";

  export default {
    name: "App",
    components: {
      Navbar,
      Burger,
      Home
    }
  }
</script>

<style src="./App.css"></style>

