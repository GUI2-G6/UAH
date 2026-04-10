<template>
    <div id="burger" :class="{
        'active': active
    }">
        <!--Logo-->
        <img src="../images/logo.png" width="75px" height="75px" alt="logo" @click="goTo('/home')">
        <!--Burger-Button-->
        <button type="button" class="burger-button " title="Menu" @click = "toggleActive">
            <span class="burger-bar" id="b-bar1"></span>
            <span class="burger-bar" id="b-bar2"></span>
            <span class="burger-bar" id="b-bar3"></span>
        </button>
        <div class="menu">
            <!--Notification-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/notifications')">
                <img src="../images/placeholder/REMINDERICON_LIGHT.png" alt="Notifications" width="30px" height="28px">
                <span v-if="active" class="label">Notifications</span>
            </button>
            <!--Application-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/application')">
                <img src="../images/placeholder/APPLICATIONS_LIGHT.png" alt="Applications" width="30px" height="28px">
                <span v-if="active" class="label">Applications</span>
            </button>
            <!--Analytics-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/analytics')">
                <img src="../images/placeholder/ANALYTICS_LIGHT.png" alt="Analytics" width="30px" height="28px">
                <span v-if="active" class="label">Analytics</span>
            </button>
            <!--Timeline-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/timeline')">
                <img src="../images/placeholder/TIMELINE_LIGHT.png" alt="Timeline" width="30px" height="28px">
                <span v-if="active" class="label">Timeline</span>
            </button>
            <!--Job-Board-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/job-board')">
                <img src="../images/placeholder/JOBBOARD_LIGHT.png" alt="Job Board" width="30px" height="28px">
                <span v-if="active" class="label">Jobs</span>
            </button>
            <!--Resumes-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/resumes')">
                <img src="../images/placeholder/RESUME_LIGHT.png" alt="Resumes" width="30px" height="28px">
                <span v-if="active" class="label">Resumes</span>
            </button>
            <!--Settings-Button-->
            <button width="50px" height="50px" class="burger-item" @click="goTo('/settings')">
                <img src="../images/placeholder/SETTING_LIGHT.png" alt="Settings" width="30px" height="28px">
                <span v-if="active" class="label">Settings</span>
            </button>
        </div>

        <div class="burger-bottom">
            <div class="user-summary" v-if="currentUser">
                <div class="user-name">{{ displayUsername }}</div>
                <div class="user-email" v-if="currentUser.email">{{ currentUser.email }}</div>
            </div>

            <button type="button" class="logout-button" @click="logout">
                Logout
            </button>
        </div>

        <ConfirmModal
            v-if="confirmLogoutOpen"
            title="Log out"
            message="Are you sure you want to log out?"
            cancelText="No, go back"
            confirmText="Yes, log out"
            @cancel="confirmLogoutOpen = false"
            @confirm="confirmLogout"
        />
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
    import { clearAuth, getCurrentUser } from "../lib/auth.js";
    import ConfirmModal from "./ConfirmModal.vue";

    export default{
        name: "Burger",
        components: {
            ConfirmModal,
        },
        data() {
            return {
                active:false,
                currentUser: null,
                _onUserUpdated: null,
                confirmLogoutOpen: false,
            };
        },
        computed: {
            displayUsername() {
                return this.currentUser?.username || 'User'
            }
        },
        mounted() {
            this.currentUser = getCurrentUser()
            this._onUserUpdated = () => {
                this.currentUser = getCurrentUser()
            }
            window.addEventListener('uah-user-updated', this._onUserUpdated)
        },
        beforeUnmount() {
            if (this._onUserUpdated) {
                window.removeEventListener('uah-user-updated', this._onUserUpdated)
            }
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
                this.confirmLogoutOpen = true
            },
            confirmLogout() {
                clearAuth();
                this.active = false;
                this.confirmLogoutOpen = false;
                this.$router.push('/login');
            }
        }
    }
</script>

<style src="./css/Burger.css"></style>