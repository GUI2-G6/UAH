<template>
    <div class="page">
        <div class="greeting">
            <h1>Home</h1>
            <p>Good afternoon, Test User Demo! You have 1 new reminder for today. Welcome!</p> <!-- Add links to actual variables here! -->
        </div>
        <div class="dashboard">
            <div class="card">
                <h1>Applied: 0</h1>
            </div>
            <div class="card">
                <h1>Interviews: 0</h1>
            </div>
            <div class="card">
                <h1>Offers: 0</h1>
            </div>
            <div class="card">
                <h1>Rejected: 0</h1>
            </div>
            <div class="card big-card">
                <h2>Recent Applications</h2>
            </div>
        </div>
    </div>
</template>

<script>
    export default{
        name: "Home"
    }
</script>

<style scoped src="./css/Home.css"></style>