<template>
    <div class="page">
        <div class="greeting">
            <h1>Home</h1>
            <p>Good afternoon, Test User Demo! You have 1 new reminder for today. Welcome!</p> <!-- Add links to actual variables here! -->
        </div>
        <div class="dashboard">
            <Card>
                <template #header>
                    <h2>Applications</h2>
                </template>
                <template #tab>
                    <h3>Updated: 7/4/2026</h3>
                </template>
                <p>{{ stats.applied }}</p>
            </Card>
            <Card>
                <template #header>
                    <h2>Interviews</h2>
                </template>
                <p>{{ stats.interviews }}</p>
            </Card>
            <Card>
                <template #header>
                    <h2>Offers</h2>
                </template>  
                <p>{{ stats.offers }}</p>
            </Card>
            <Card>
                <template #header>
                    <h2>Rejected</h2>
                </template>
                <p>{{ stats.rejected }}</p>
            </Card>
            <Card class="big-card">
                <h2>Recent Applications</h2>
            </Card>
        </div>
    </div>
</template>

<script>
    import Card from "../components/Card.vue"
    export default{
        data() {
            return {
                stats: {
                    applied: 1,
                    interviews: 2,
                    offers: 3,
                    rejected: 4,
                    recent_applications: []
                }
            }
        },
        components: {
            Card
        },
        name: "Home"
    }
</script>

<style scoped src="./css/Home.css"></style>

<!--
<template>
    <Card>
        <template #header>
            <h3>{{ job.title }}</h3>
        </template>
        <p>{{ job.company }}</p>
        <p>{{ job.location }}</p>
        <button @click="apply">Apply</button>  
    </Card>
</template>

<script>
import Card from "./Card.vue";
export default {
    name: "JobPosting",
    components: {
        Card
    },
    props: {
        job: Object
    },
    methods: {
        apply() {
            console.log("Applying to", this.job.title);
        }
    }
}
</script>

<style scoped>
.job-card {
    background: #f5f5f5;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}
</style>
-->