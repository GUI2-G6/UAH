<template>
    <div class="page">
        <div class="greeting">
            <h1>Settings</h1>
        </div>
        <div class="dashboard">
            <Card>
                <template #header>
                    <h3>Profile Settings</h3>
                </template>
                <p>Full Name:</p>
                <input type="text"> <!--v-model="name" (potential for updating variables)-->
                <p>Job Title:</p>
                <input type="text">
            </Card>
            <Card>
                <template #header>
                    <h3>Notifications</h3>
                </template>
                <h4>Email Notifications</h4>
                <h4>Reminder Notifications</h4>
                <h4>Application Status Updates</h4>
            </Card>
            <Card>
                <template #header>
                    <h3>Account & Security</h3>
                </template>
                <h4>Change Email</h4>
                <h4>Change Password</h4>
            </Card>
            <Card>
                <template #header>
                    <h3>Preferences</h3>
                </template>
                <h4>Language</h4>
                <h4>Timezone</h4>
            </Card>

        </div>
    </div>

</template>

<script>
import Card from "../components/Card.vue";

export default {
  name: "Settings",
  components: {
    Card
  }
}
</script>

<style scoped src="./css/Settings.css"></style>