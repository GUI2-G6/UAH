<template>
    <div class="page">
        <div class="greeting">
            <h1>Home</h1>
            <p>Good afternoon, Test User Demo! You have 1 new reminder for today. Welcome!</p> <!-- Add links to actual variables here! -->
        </div>
        <div class="dashboard">
            <Card>
                <h2>Applied: 0</h2>
            </Card>
            <Card>
                <h2>Interviews: 0</h2>
            </Card>
            <Card>
                <h2>Offers: 0</h2>
            </Card>
            <Card>
                <h2>Rejected: 0</h2>
            </Card>
            <Card class="big-card">
                <h2>Recent Applications</h2>
            </Card>
        </div>
    </div>
</template>

<script>
    import Card from "../components/Card.vue";

    export default{
        components: {
            Card
        },
        name: "Home"
    }
</script>

<style scoped src="./css/Home.css"></style>