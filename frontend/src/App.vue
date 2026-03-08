<template>
  <div id="uah-app">
    <header>
      <h1><router-link to="/" class="logo-link">UAH</router-link></h1>
      <p class="subtitle">Unified Application Hub</p>
      <Navbar />
    </header>
    <router-view />
  </div>
</template>

<script>
import Navbar from "./components/Navbar.vue"

export default {
  name: "App",
  components: {
    Navbar
  }
}
</script>

<style src="./App.css"></style>

