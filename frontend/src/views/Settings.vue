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
                <h5>Email Notifications</h5>
            </Card>
            <Card>
                <template #header>
                    <h3>Account & Security</h3>
                </template>
                <p>Full Name:</p>
                <input type="text"> <!--v-model="name" (potential for updating variables)-->
                <p>Job Title:</p>
                <input type="text">
            </Card>
            <Card>
                <template #header>
                    <h3>Preferences</h3>
                </template>
                <p>Full Name:</p>
                <input type="text"> <!--v-model="name" (potential for updating variables)-->
                <p>Job Title:</p>
                <input type="text">
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

<style src="./css/Settings.css"></style>