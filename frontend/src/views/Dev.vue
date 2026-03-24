<template>
  <div id="uah-app">
    <header>
      <h1><router-link to="/" class="logo-link">UAH</router-link></h1>
      <p class="subtitle">Unified Application Hub</p>
      <Navbar />
      <Burger />
    </header>
    <router-view />
  </div>
</template>

<script>
import Navbar from "../components/Navbar.vue"
import Burger from "../components/Burger.vue";

export default {
  name: "App",
  components: {
    Navbar,
    Burger
  }
}
</script>

<style scoped src="./css/Dev.css"></style>