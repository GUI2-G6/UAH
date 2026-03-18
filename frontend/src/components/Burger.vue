<template>
    <div id="burger" :class="{
        'active': active
    }" @click = "toggleActive">
        <!--Logo-->
        <img src="../images/logo.png" width="75px" height="75px" alt="logo">
        <br>
        <!--Burger-Button-->
        <button type="button" class="burger-button " title="Menu">
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
            <img src="../images/home.png" alt="Notifications" width="30px" height="28px">
        </button>
        <br>
        <!--Application-Button-->
        <button width="50px" height="50px" class="burger-item" id="application-button">
            <img src="../images/home.png" alt="Applications" width="30px" height="28px">
        </button>
        <br>
        <!--Analytics-Button-->
        <button width="50px" height="50px" class="burger-item" id="analytics-button">
            <img src="../images/home.png" alt="Analytics" width="30px" height="28px">
        </button>
        <br>
        <!--Timeline-Button-->
        <button width="50px" height="50px" class="burger-item" id="timeline-button">
            <img src="../images/home.png" alt="Timeline" width="30px" height="28px">
        </button>
        <br>
        <!--Job-Board-Button-->
        <button width="50px" height="50px" class="burger-item" id="job-board-button">
            <img src="../images/home.png" alt="Job Board" width="30px" height="28px">
        </button>
        <br>
        <!--Resumes-Button-->
        <button width="50px" height="50px" class="burger-item" id="Resumes-button">
            <img src="../images/home.png" alt="Resumes" width="30px" height="28px">
        </button>
        <br>
            <!--Import-Resume-Button-->
            <!--Applicant-Info-Button-->
            <!--Job-Application-Information-Button-->
        <!--Settings-Button-->
        <button width="50px" height="50px" class="burger-item" id="Settings-button">
            <img src="../images/home.png" alt="Settings" width="30px" height="28px">
        </button>
        <br>
            <!--Preferences-->
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