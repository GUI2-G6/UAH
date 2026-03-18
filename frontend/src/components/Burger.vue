<template>
    <div id="burger" :class="{
        'active': active
    }" @click = "toggleActive">
        <img src="../images/logo.png" width="75px" height="75px">Logo</img> <!--Logo isn't working right now-->
        <button type="button" class="burger-button " title="Menu">
            <span class="burger-bar" id="b-bar1"></span>
            <span class="burger-bar" id="b-bar2"></span>
            <span class="burger-bar" id="b-bar3"></span>
        </button>
            <!--Logo-->
            <!--Hamburger-Button-->
            <!--Home-Button-->
            <!--Notification-Button-->
            <!--Application-Button-->
            <!--Analytics-Button-->
            <!--Timeline-Button-->
            <!--Job-Board-Button-->
            <!--Resumes-Button-->
                <!--Import-Resume-Button-->
                <!--Applicant-Info-Button-->
                <!--Job-Application-Information-Button-->
            <!--Settings-Button-->
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