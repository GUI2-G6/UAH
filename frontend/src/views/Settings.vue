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
                <p v-if="currentUser" class="signed-in">
                    Signed in as: <strong>{{ displayName }}</strong>
                    <span v-if="currentUser.email">({{ currentUser.email }})</span>
                </p>
                <p>Full Name:</p>
                <input type="text" v-model="fullName"> <!--v-model="name" (potential for updating variables)-->
                <p>Job Title:</p>
                <input type="text" v-model="jobTitle">
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
    },
    data() {
        return {
            currentUser: null,
            fullName: '',
            jobTitle: '',
        }
    },
    computed: {
        displayName() {
            if (!this.currentUser) return ''
            const first = this.currentUser.first_name || this.currentUser.firstName
            const last = this.currentUser.last_name || this.currentUser.lastName
            const full = [first, last].filter(Boolean).join(' ').trim()
            return full || this.currentUser.username || 'User'
        }
    },
    async mounted() {
        await this.loadUser()
    },
    methods: {
        async loadUser() {
            try {
                const raw = localStorage.getItem('uah_current_user')
                this.currentUser = raw ? JSON.parse(raw) : null
            } catch {
                this.currentUser = null
            }

            if (this.currentUser) {
                const first = this.currentUser.first_name || this.currentUser.firstName
                const last = this.currentUser.last_name || this.currentUser.lastName
                const full = [first, last].filter(Boolean).join(' ').trim()
                this.fullName = full || this.currentUser.username || ''
            }

            const host = window.location.hostname
            const isLocalDev = host === 'localhost' || host === '127.0.0.1' || host === '::1'
            const token = localStorage.getItem('uah_access_token')
            if (!token || isLocalDev) return

            // Refresh from backend if available.
            try {
                const res = await fetch('/api/auth/me', {
                    headers: { Authorization: `Bearer ${token}` },
                })
                if (!res.ok) return
                const user = await res.json()
                this.currentUser = user
                localStorage.setItem('uah_current_user', JSON.stringify(user))

                const first = user.first_name || user.firstName
                const last = user.last_name || user.lastName
                const full = [first, last].filter(Boolean).join(' ').trim()
                this.fullName = full || user.username || this.fullName
            } catch {
                // ignore (backend may be down)
            }
        },
    },
}
</script>

<style scoped src="./css/Settings.css"></style>