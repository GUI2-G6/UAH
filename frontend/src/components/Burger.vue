<template>
    <div id="burger" :class="{
        'active': active
    }">
        <!--Logo-->
        <img src="../images/logo.png" width="75px" height="75px" alt="logo">
        <br>
        <!--Burger-Button-->
        <button type="button" class="burger-button " title="Menu" @click = "toggleActive">
            <span class="burger-bar" id="b-bar1"></span>
            <span class="burger-bar" id="b-bar2"></span>
            <span class="burger-bar" id="b-bar3"></span>
        </button>
        <br>
        <!--Home-Button-->
        <button width="50px" height="50px" class="burger-item" id="home-button">
            <img src="../images/placeholder/HOMEICON_LIGHT.png" alt="Home" width="30px" height="28px">
        </button>
        <br>
        <!--Notification-Button-->
        <button width="50px" height="50px" class="burger-item" id="notification-button">
            <img src="../images/placeholder/REMINDERICON_LIGHT.png" alt="Notifications" width="30px" height="28px">
        </button>
        <br>
        <!--Application-Button-->
        <button width="50px" height="50px" class="burger-item" id="application-button">
            <img src="../images/placeholder/APPLICATIONS_LIGHT.png" alt="Applications" width="30px" height="28px">
        </button>
        <br>
        <!--Analytics-Button-->
        <button width="50px" height="50px" class="burger-item" id="analytics-button">
            <img src="../images/placeholder/ANALYTICS_LIGHT.png" alt="Analytics" width="30px" height="28px">
        </button>
        <br>
        <!--Timeline-Button-->
        <button width="50px" height="50px" class="burger-item" id="timeline-button">
            <img src="../images/placeholder/TIMELINE_LIGHT.png" alt="Timeline" width="30px" height="28px">
        </button>
        <br>
        <!--Job-Board-Button-->
        <button width="50px" height="50px" class="burger-item" id="job-board-button">
            <img src="../images/placeholder/JOBBOARD_LIGHT.png" alt="Job Board" width="30px" height="28px">
        </button>
        <br>
        <!--Resumes-Button-->
        <button width="50px" height="50px" class="burger-item" id="resumes-button">
            <img src="../images/home.png" alt="Resumes" width="30px" height="28px">
            <!--Import-Resume-Button-->
            <button width="50px" height="50px" class="burger-item" id="import-resumes-button">
                <img src="../images/home.png" alt="Import Resume" width="15px" height="14px">
            </button>
            <!--Applicant-Info-Button-->
            <button width="50px" height="50px" class="burger-item" id="applicant-info-button">
                <img src="../images/home.png" alt="Applicant info" width="15px" height="14px">
            </button>
            <!--Job-Application-Information-Button-->
            <button width="50px" height="50px" class="burger-item" id="job-application-info-button">
                <img src="../images/home.png" alt="Job Application info" width="15px" height="14px">
            </button>
        </button>
        <br>
        <!--Settings-Button-->
        <button width="50px" height="50px" class="burger-item" id="Settings-button">
            <img src="../images/home.png" alt="Settings" width="30px" height="28px">
            <!--Preferences-->
            <button width="50px" height="50px" class="burger-item" id="preferences-button">
                <img src="../images/home.png" alt="Preferences" width="15px" height="14px">
            </button>
        </button>
        <br>
    </div>
</template>

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
            }
        }
    }
</script>

<style src="./css/Burger.css"></style>