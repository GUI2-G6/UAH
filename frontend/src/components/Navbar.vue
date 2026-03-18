<template>
    <nav class="nav">
        <router-link to="/" class="nav-link">Home</router-link>
        <router-link to="/status" class="nav-link">Status</router-link>
    </nav>
</template>

<!--Exports the Navbar so other files can see and use it-->
<script>
    export default{
        name: "Navbar"
    }
</script>

<style src="./css/Navbar.css"></style>