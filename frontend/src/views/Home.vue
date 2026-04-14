<template>
    <div class="page">
        <div class="greeting">
            <h1>Home</h1>
            <p>Good afternoon, {{displayName}}! You have 1 new reminder for today. Welcome!</p> <!-- Add links to actual variables here! -->
        </div>
        <div class="dashboard">
            <Card class="home-card home-stat-card">
                <template #header>
                    <h2>Applications</h2>
                </template>
                <template #tab>
                    <h3>Updated: 7/4/2026</h3>
                </template>
                <p id="applied">{{ stats.applied }}</p>
            </Card>
            <Card class="home-card home-stat-card">
                <template #header>
                    <h2>Interviews</h2>
                </template>
                <template #tab>
                    <h3>Updated: 4/11/2026</h3>
                </template>
                <p id="interviews">{{ stats.interviews }}</p>
            </Card>
            <Card class="home-card home-stat-card">
                <template #header>
                    <h2>Offers</h2>
                </template>  
                <template #tab>
                    <h3>Updated: 8/2/1992</h3>
                </template>
                <p id="offers">{{ stats.offers }}</p>
            </Card>
            <Card class="home-card home-stat-card">
                <template #header>
                    <h2>Rejected</h2>
                </template>
                <template #tab>
                    <h3>Updated: 4/11/2026</h3>
                </template>
                <p id="rejected">{{ stats.rejected }}</p>
            </Card>
            <Card class="home-card home-card--wide">
                <template #header>
                    <h2 id="tracked-applications">Tracked Applications</h2>
                    <p>Filter</p>
                    <select id="app-filter">
                        <option>Newest</option>
                        <option>Oldest</option>
                        <option>Accepted</option>
                    </select>
                </template>
                <Card variant="minimal" class="home-application-card">
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
                <Card variant="minimal" class="home-application-card">
                    <Application :application="{
                    company: 'IBM',
                    role: 'Data Analyst',
                    dateSent: '4/11/2026',
                    statusStep: 3,
                    maxStep: 4,
                    statusText: 'Offer',
                    noResponse: false
                    }" />
                </Card>
                <Card variant="minimal" class="home-application-card">
                    <Application :application="{
                    company: 'Apple',
                    role: 'Server Manager',
                    dateSent: '4/14/2026',
                    statusStep: 2,
                    maxStep: 4,
                    statusText: 'Interview',
                    noResponse: false
                    }" />
                </Card>
                <Card variant="minimal" class="home-application-card">
                    <Application :application="{
                    company: 'Microsoft',
                    role: 'Quality Assurance',
                    dateSent: '4/15/2026',
                    statusStep: 1,
                    maxStep: 4,
                    statusText: 'Applied',
                    noResponse: false
                    }" />
                </Card>
                <Card variant="minimal" class="home-application-card">
                    <Application :application="{
                    company: 'Nvidia',
                    role: 'CEO',
                    dateSent: '4/1/2026',
                    statusStep: 1,
                    maxStep: 4,
                    statusText: 'Applied',
                    noResponse: true
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