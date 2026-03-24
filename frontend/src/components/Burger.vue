<template>
    <div id="burger" :class="{
        'active': active
    }">
        <!--Logo-->
        <img src="../images/logo.png" width="75px" height="75px" alt="logo">
        <!--Burger-Button-->
        <button type="button" class="burger-button " title="Menu" @click = "toggleActive">
            <span class="burger-bar" id="b-bar1"></span>
            <span class="burger-bar" id="b-bar2"></span>
            <span class="burger-bar" id="b-bar3"></span>
        </button>
        <div class="menu" v-if="active">
            <!--Home-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/home')">
                <img src="../images/placeholder/HOMEICON_LIGHT.png" alt="Home" width="30px" height="28px">
            </button>
            <!--Notification-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/notifications')">
                <img src="../images/placeholder/REMINDERICON_LIGHT.png" alt="Notifications" width="30px" height="28px">
            </button>
            <!--Application-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/application')">
                <img src="../images/placeholder/APPLICATIONS_LIGHT.png" alt="Applications" width="30px" height="28px">
            </button>
            <!--Analytics-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/analytics')">
                <img src="../images/placeholder/ANALYTICS_LIGHT.png" alt="Analytics" width="30px" height="28px">
            </button>
            <!--Timeline-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/timeline')">
                <img src="../images/placeholder/TIMELINE_LIGHT.png" alt="Timeline" width="30px" height="28px">
            </button>
            <!--Job-Board-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/job-board')">
                <img src="../images/placeholder/JOBBOARD_LIGHT.png" alt="Job Board" width="30px" height="28px">
            </button>
            <!--Resumes-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/resumes')">
                <img src="../images/placeholder/RESUME_LIGHT.png" alt="Resumes" width="30px" height="28px">
            </button>
            <!--Settings-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/settings')">
                <img src="../images/placeholder/SETTING_LIGHT.png" alt="Settings" width="30px" height="28px">
            </button>
        </div>

        <button type="button" class="logout-button" @click="logout">
            Logout
        </button>
    </div>
</template>

<!--
<button width="50px" height="50px" class="burger-item" id="import-resumes-button">
    <img src="../images/home.png" alt="Import Resume" width="15px" height="14px">
</button>

<button width="50px" height="50px" class="burger-item" id="applicant-info-button">
    <img src="../images/home.png" alt="Applicant info" width="15px" height="14px">
</button>

<button width="50px" height="50px" class="burger-item" id="job-application-info-button">
    <img src="../images/home.png" alt="Job Application info" width="15px" height="14px">
</button>

<button width="50px" height="50px" class="burger-item" id="preferences-button">
    <img src="../images/home.png" alt="Preferences" width="15px" height="14px">
</button>
-->

<!--Exports the HBMenu so other files can see and use it-->
<script>
    export default{
        name: "Burger",
        data() {
            return {
                active:false
            };
        },
        methods: {
            toggleActive() {
                this.active = !this.active;
            },
            goTo(route) {
                this.$router.push(route);
                this.active = false;
            },
            logout() {
                localStorage.removeItem('uah_access_token');
                this.active = false;
                this.$router.push('/login');
            }
        }
    }
</script>

<style src="./css/Burger.css"></style>