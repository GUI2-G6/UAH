<template>
    <div class="page">
        <div class="greeting">
            <h1>Notifications</h1>
            <p>Keep track of your follow-ups and deadlines</p> <!-- Add links to actual variables here! -->
        </div>
        <div class="dashboard">
            <div class="card big-card">
                <h2>No pending reminders. Great job keeping on top of things!</h2>
            </div>

            <div class="card">
                <h1>Total Pending: 0</h1>
            </div>
            <div class="card">
                <h1>Action Required: 0</h1>
            </div>
            <div class="card">
                <h1>Upcoming: 0</h1>
            </div>
        </div>
    </div>
</template>

<script>
    export default{
        name: "Notifications"
    }
</script>

<style scoped src="./css/Notifications.css"></style>