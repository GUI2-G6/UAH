<template>
    <div class="page">
        <div class="greeting">
            <h1>Home</h1>
            <p>Good afternoon, {{displayName}}! You have 1 new reminder for today. Welcome!</p> <!-- Add links to actual variables here! -->
        </div>
        <div class="dashboard">
            <Card>
                <template #header>
                    <h2>Applications</h2>
                </template>
                <template #tab>
                    <h3>Updated: 7/4/2026</h3>
                </template>
                <p id="applied">{{ stats.applied }}</p>
            </Card>
            <Card>
                <template #header>
                    <h2>Interviews</h2>
                </template>
                <template #tab>
                    <h3>Updated: 4/11/2026</h3>
                </template>
                <p id="interviews">{{ stats.interviews }}</p>
            </Card>
            <Card>
                <template #header>
                    <h2>Offers</h2>
                </template>  
                <template #tab>
                    <h3>Updated: 8/2/1992</h3>
                </template>
                <p id="offers">{{ stats.offers }}</p>
            </Card>
            <Card>
                <template #header>
                    <h2>Rejected</h2>
                </template>
                <template #tab>
                    <h3>Updated: 4/11/2026</h3>
                </template>
                <p id="rejected">{{ stats.rejected }}</p>
            </Card>
            <Card class="card big-card">
                <template #header>
                    <h2 id="tracked-applications">Tracked Applications</h2>
                </template>
                <Card class="application">
                    <Application :application="{
                    company: 'Google',
                    role: 'Software Engineer',
                    dateSent: '4/11/2026',
                    statusStep: 4,
                    maxStep: 4,
                    statusText: 'Accepted!',
                    noResponse: false
                    }" />
                </Card>
            </Card>
        </div>
    </div>
</template>

<script>
    import Card from "../components/Card.vue"
    import Application from "../components/Application.vue"
    import { getCurrentUser } from "../lib/auth.js";

    export default{
        data() {
            return {
                user: getCurrentUser(),
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
            Card,
            Application
        },
    computed: {
        displayName() {
            const first = this.user?.first_name || this.user?.firstName || ""
            const last = this.user?.last_name || this.user?.lastName || ""

            const full = `${first} ${last}`.trim()

            return full || this.user?.email || "User"
        }
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