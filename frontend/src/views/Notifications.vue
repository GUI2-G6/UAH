<template>
    <div class="page">
        <div class="greeting">
            <h1>Notifications</h1>
            <p>Keep track of your follow-ups and deadlines</p> <!-- Add links to actual variables here! -->
        </div>
        <div class="dashboard">
            <Card class="notifications-card notifications-card--wide">
                <h2>No pending reminders. Great job keeping on top of things!</h2>
            </Card>
            <Card class="notifications-card">
                <h2>Total Pending: 0</h2>
            </Card>
            <Card class="notifications-card">
                <h2>Action Required: 0</h2>
            </Card>
            <Card class="notifications-card">
                <h2>Upcoming: 0</h2>
            </Card>
        </div>
    </div>
</template>

<script>
    import Card from '@/components/Card.vue';

    export default{
        name: "Notifications",
        components:{
            Card
        }
    }
</script>

<style scoped src="./css/Notifications.css"></style>
