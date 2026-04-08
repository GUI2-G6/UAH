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
                <div class="settings-group">
                    <p v-if="currentUser" class="signed-in">
                        Signed in as: <strong>{{ currentUser.username || 'User' }}</strong>
                        <span v-if="currentUser.email">({{ currentUser.email }})</span>
                    </p>
                    <p v-if="currentUser && currentUser.email" class="email-status" :class="{ 'is-verified': !!currentUser.email_verified }">
                        Email status: <strong>{{ currentUser.email_verified ? 'Verified' : 'Not verified' }}</strong>
                    </p>
                    <p v-if="currentUser" class="current-value">
                        Current name: <strong>{{ (currentUser.first_name || currentUser.firstName || '') + (currentUser.last_name || currentUser.lastName ? ' ' + (currentUser.last_name || currentUser.lastName) : '') || 'Not set' }}</strong>
                    </p>
                    <p>First Name</p>
                    <input type="text" v-model="firstName">
                    <p>Last Name</p>
                    <input type="text" v-model="lastName">
                    <button @click="changeName" :disabled="working" :class="buttonStatusClass('changeName')">Update name</button>
                    <div v-if="actionStatus.changeName.message" :class="feedbackClass('changeName')">
                        {{ actionStatus.changeName.message }}
                    </div>
                </div>
            </Card>
            <Card>
                <template #header>
                    <h3>Account & Security</h3>
                </template>
                <div class="settings-group">
                    <h4>Change Username</h4>
                    <p v-if="currentUser" class="current-value">Current: <strong>{{ currentUser.username || 'User' }}</strong></p>
                    <input type="text" v-model="changeUsernameNew" placeholder="New username">
                    <input type="text" v-model="changeUsernameNewConfirm" placeholder="Confirm new username">
                    <button @click="changeUsername" :disabled="working" :class="buttonStatusClass('changeUsername')">Update username</button>
                    <div v-if="actionStatus.changeUsername.message" :class="feedbackClass('changeUsername')">
                        {{ actionStatus.changeUsername.message }}
                    </div>
                </div>

                <div class="settings-group">
                    <h4>Change Email</h4>
                    <p v-if="currentUser" class="current-value">Current: <strong>{{ currentUser.email || 'Not set' }}</strong></p>
                    <input type="email" v-model="changeEmailNew" placeholder="New email">
                    <input type="email" v-model="changeEmailNewConfirm" placeholder="Confirm new email">
                    <button @click="changeEmail" :disabled="working" :class="buttonStatusClass('changeEmail')">Update email</button>
                    <div v-if="actionStatus.changeEmail.message" :class="feedbackClass('changeEmail')">
                        {{ actionStatus.changeEmail.message }}
                    </div>
                </div>

                <div class="settings-group">
                    <h4>Change Password</h4>
                    <form @submit.prevent="changePassword">
                        <input type="text" autocomplete="username" style="display:none" aria-hidden="true" />
                        <SecretInput v-model="currentPassword" placeholder="Current password" autocomplete="current-password" :disabled="working" />
                        <SecretInput v-model="newPassword" placeholder="New password" autocomplete="new-password" :disabled="working" />
                        <SecretInput v-model="confirmNewPassword" placeholder="Confirm new password" autocomplete="new-password" :disabled="working" />
                        <button type="submit" :disabled="working" :class="buttonStatusClass('changePassword')">Update password</button>
                    </form>
                    <div v-if="actionStatus.changePassword.message" :class="feedbackClass('changePassword')">
                        {{ actionStatus.changePassword.message }}
                    </div>
                </div>

                <div class="settings-group">
                    <h4>Email Verification</h4>
                    <button @click="sendVerification" :disabled="working" :class="buttonStatusClass('sendVerification')">Send verification token</button>
                    <div v-if="actionStatus.sendVerification.message" :class="feedbackClass('sendVerification')">
                        {{ actionStatus.sendVerification.message }}
                    </div>
                    <form @submit.prevent="verifyEmail">
                        <SecretInput v-model="verifyToken" placeholder="Verification token" autocomplete="off" :disabled="working" />
                        <button type="submit" :disabled="working" :class="buttonStatusClass('verifyEmail')">Verify email</button>
                    </form>
                    <div v-if="actionStatus.verifyEmail.message" :class="feedbackClass('verifyEmail')">
                        {{ actionStatus.verifyEmail.message }}
                    </div>
                </div>

                <div class="settings-group">
                    <h4>Delete Account</h4>
                    <button class="danger" @click="openDeleteConfirm" :disabled="working" :class="buttonStatusClass('deleteAccount')">Delete account</button>
                    <div v-if="actionStatus.deleteAccount.message" :class="feedbackClass('deleteAccount')">
                        {{ actionStatus.deleteAccount.message }}
                    </div>
                </div>
            </Card>
            <Card>
                <template #header>
                    <h3>Notifications & Preferences</h3>
                </template>
                <div class="settings-group">
                    <h4>Email Notifications</h4>
                    <!--Using a select box here is obtrusive and bad. Redesign it to be a switch.-->
                    <select name="email-notifications" id="email-notifications">
                        <option>Yes</option>
                        <option>No</option>
                    </select>
                    <h4>Reminder Notifications</h4>
                    <!--Using a select box here is obtrusive and bad. Redesign it to be a switch.-->
                    <select name="reminder-notifications" id="reminder-notifications">
                        <option>Yes</option>
                        <option>No</option>
                    </select>
                    <h4>Application Status Updates</h4>
                    <!--Using a select box here is obtrusive and bad. Redesign it to be a switch.-->
                    <select name="application-status-updates" id="application-status-updates">
                        <option>Yes</option>
                        <option>No</option>
                    </select>
                </div>
                <div class="settings-group">
                    <h4>Language</h4>
                    <select name="language" id="language">
                        <option>English</option>
                        <option>Spanish</option>
                        <option>French</option>
                    </select>
                    <h4>Timezone</h4>
                    <select name="timezone" id="timezone">
                        <option>Eastern Standard Time (EST)</option>
                        <option>Central Standard Time (CST)</option>
                        <option>Mountain Standard Time (MST)</option>
                        <option>Pacific Standard Time (PST)</option>
                    </select>
                </div>
            </Card>

        </div>

        <ConfirmModal
            v-if="confirmDeleteOpen"
            title="Delete account"
            message="Are you sure you want to delete your account? This cannot be undone."
            cancelText="No, go back"
            confirmText="Yes, delete my account"
            :busy="working"
            @cancel="confirmDeleteOpen = false"
            @confirm="confirmDeleteAccount"
        />
    </div>

</template>

<script>
import Card from "../components/Card.vue";
import ConfirmModal from "../components/ConfirmModal.vue";
import SecretInput from "../components/SecretInput.vue";
import { authedFetch, clearAuth, setCurrentUser } from "../lib/auth.js";
import { showToast } from '@/services/toastService.js';

export default {
  name: "Settings",
  components: {
        Card,
        ConfirmModal,
        SecretInput,
    },
    data() {
        return {
            currentUser: null,
            firstName: '',
            lastName: '',

            working: false,
            actionStatus: {
                changeName: { state: 'idle', message: '' },
                changeUsername: { state: 'idle', message: '' },
                changeEmail: { state: 'idle', message: '' },
                changePassword: { state: 'idle', message: '' },
                sendVerification: { state: 'idle', message: '' },
                verifyEmail: { state: 'idle', message: '' },
                deleteAccount: { state: 'idle', message: '' },
            },
            _actionTimers: {},

            changeUsernameNew: '',
            changeUsernameNewConfirm: '',

            changeEmailNew: '',
            changeEmailNewConfirm: '',

            currentPassword: '',
            newPassword: '',
            confirmNewPassword: '',

            verifyToken: '',

            confirmDeleteOpen: false,
        }
    },
    computed: {},
    async mounted() {
        await this.loadUser()
    },
    methods: {
        setActionStatus(key, state, message) {
            if (this._actionTimers[key]) {
                clearTimeout(this._actionTimers[key])
                this._actionTimers[key] = null
            }

            if (!this.actionStatus[key]) {
                this.actionStatus[key] = { state: 'idle', message: '' }
            }

            this.actionStatus[key].state = state
            this.actionStatus[key].message = message || ''

            if (state === 'success' || state === 'error') {
                this._actionTimers[key] = setTimeout(() => {
                    if (this.actionStatus[key]) {
                        this.actionStatus[key].state = 'idle'
                        this.actionStatus[key].message = ''
                    }
                    this._actionTimers[key] = null
                }, 3500)
            }
        },
        buttonStatusClass(key) {
            const state = this.actionStatus?.[key]?.state
            return {
                'btn-working': state === 'working',
                'btn-success': state === 'success',
                'btn-error': state === 'error',
            }
        },
        feedbackClass(key) {
            const state = this.actionStatus?.[key]?.state
            return {
                'action-feedback': true,
                'is-success': state === 'success',
                'is-error': state === 'error',
            }
        },
        formatFailure(label, e) {
            const msg = e?.message ?? String(e)
            if (!msg) return `${label} failed`
            if (msg.startsWith('HTTP ')) return `${label} failed (${msg})`
            return `${label} failed: ${msg}`
        },
        async loadUser() {
            try {
                const raw = localStorage.getItem('uah_current_user')
                this.currentUser = raw ? JSON.parse(raw) : null
            } catch {
                this.currentUser = null
            }

            if (this.currentUser) {
                this.firstName = this.currentUser.first_name || this.currentUser.firstName || ''
                this.lastName = this.currentUser.last_name || this.currentUser.lastName || ''
            }

            const host = window.location.hostname
            const isLocalDev = host === 'localhost' || host === '127.0.0.1' || host === '::1'
            if (isLocalDev) return

            // Refresh from backend if available.
            try {
                const res = await authedFetch('/api/auth/me')
                if (!res.ok) return
                const user = await res.json()
                this.currentUser = user
                localStorage.setItem('uah_current_user', JSON.stringify(user))

                this.firstName = user.first_name || user.firstName || this.firstName
                this.lastName = user.last_name || user.lastName || this.lastName
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated') {
                    this.$router.push('/login')
                }
                // otherwise ignore (backend may be down)
            }
        },

        async changeName() {
            if (!this.firstName || !this.lastName) {
                this.setActionStatus('changeName', 'error', 'First and last name are required');
                showToast('Please fill out all required fields', 'error');
                return;
            }

            this.working = true
            this.setActionStatus('changeName', 'working', 'Updating…')
            try {
                const res = await authedFetch('/api/account/change-name', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        first_name: this.firstName,
                        last_name: this.lastName,
                    }),
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)

                this.currentUser = data
                setCurrentUser(data)
                this.setActionStatus('changeName', 'success', 'Name updated')
                showToast('Name updated successfully!', 'success');
            } catch (e) {
                this.setActionStatus('changeName', 'error', this.formatFailure('Update name', e))
                showToast('Failed to update name: ' + e.message, 'error');
            } finally {
                this.working = false
            }
        },

        async changePassword() {
            if (!this.newPassword || !this.confirmNewPassword) {
                this.setActionStatus('changePassword', 'error', 'Please enter and confirm your new password')
                return
            }
            if (this.newPassword !== this.confirmNewPassword) {
                this.setActionStatus('changePassword', 'error', 'New passwords do not match')
                return
            }
            this.working = true
            this.setActionStatus('changePassword', 'working', 'Updating…')
            try {
                const res = await authedFetch('/api/account/change-password', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        current_password: this.currentPassword,
                        new_password: this.newPassword,
                    }),
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                this.setActionStatus('changePassword', 'success', data?.message || 'Password changed successfully')
                this.currentPassword = ''
                this.newPassword = ''
                this.confirmNewPassword = ''
            } catch (e) {
                this.setActionStatus('changePassword', 'error', this.formatFailure('Update password', e))
            } finally {
                this.working = false
            }
        },

        async changeEmail() {
            const newEmail = (this.changeEmailNew || '').trim()
            const newEmailConfirm = (this.changeEmailNewConfirm || '').trim()
            if (!newEmail || !newEmailConfirm) {
                const msg = 'Please enter and confirm your new email'
                this.setActionStatus('changeEmail', 'error', msg)
                showToast(msg, 'error')
                return
            }
            if (newEmail.toLowerCase() !== newEmailConfirm.toLowerCase()) {
                const msg = 'Emails do not match'
                this.setActionStatus('changeEmail', 'error', msg)
                showToast(msg, 'error')
                return
            }
            const emailRegex = "/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i"
            if (!emailRegex.test(newEmail)) {
                const msg = 'Please enter a valid email address'
                this.setActionStatus('changeEmail', 'error', msg)
                showToast(msg, 'error')
                return
            }
            this.working = true
            this.setActionStatus('changeEmail', 'working', 'Updating…')
            try {
                const res = await authedFetch('/api/account/change-email', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        new_email: newEmail,
                    }),
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                this.setActionStatus('changeEmail', 'success', data?.message || 'Email updated')
                showToast('Email updated successfully!', 'success')
                this.changeEmailNewConfirm = ''

                // Ensure client reflects reverification immediately.
                if (this.currentUser) {
                    const updated = {
                        ...this.currentUser,
                        email: newEmail,
                        email_verified: false,
                    }
                    this.currentUser = updated
                    setCurrentUser(updated)
                }

                await this.loadUser()
            } catch (e) {
                const msg = this.formatFailure('Update email', e)
                this.setActionStatus('changeEmail', 'error', msg)
                showToast(msg, 'error')
            } finally {
                this.working = false
            }
        },

        async changeUsername() {
            const newUsername = (this.changeUsernameNew || '').trim()
            const newUsernameConfirm = (this.changeUsernameNewConfirm || '').trim()
            if (!newUsername || !newUsernameConfirm) {
                const msg = 'Please enter and confirm your new username'
                this.setActionStatus('changeUsername', 'error', msg)
                showToast(msg, 'error')
                return
            }
            if (newUsername !== newUsernameConfirm) {
                const msg = 'Usernames do not match'
                this.setActionStatus('changeUsername', 'error', msg)
                showToast(msg, 'error')
                return
            }
            this.working = true
            this.setActionStatus('changeUsername', 'working', 'Updating…')
            try {
                const res = await authedFetch('/api/account/change-username', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        new_username: newUsername,
                    }),
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)

                // Endpoint returns UserResponse
                this.currentUser = data
                setCurrentUser(data)
                this.setActionStatus('changeUsername', 'success', 'Username updated')
                showToast('Username updated successfully!', 'success')
                this.changeUsernameNewConfirm = ''
            } catch (e) {
                const msg = this.formatFailure('Update username', e)
                this.setActionStatus('changeUsername', 'error', msg)
                showToast(msg, 'error') // ✅ add
            } finally {
                this.working = false
            }
        },

        async sendVerification() {
            this.working = true
            this.setActionStatus('sendVerification', 'working', 'Sending…')
            try {
                const res = await authedFetch('/api/account/send-verification', {
                    method: 'POST',
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                this.setActionStatus('sendVerification', 'success', data?.message || 'Verification sent')
            } catch (e) {
                this.setActionStatus('sendVerification', 'error', this.formatFailure('Send verification', e))
            } finally {
                this.working = false
            }
        },

        async verifyEmail() {
            this.working = true
            this.setActionStatus('verifyEmail', 'working', 'Verifying…')
            try {
                const res = await fetch('/api/account/verify-email', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: this.verifyToken }),
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                this.setActionStatus('verifyEmail', 'success', data?.message || 'Email verified')
                this.verifyToken = ''
                await this.loadUser()
            } catch (e) {
                this.setActionStatus('verifyEmail', 'error', this.formatFailure('Verify email', e))
            } finally {
                this.working = false
            }
        },

        openDeleteConfirm() {
            this.confirmDeleteOpen = true
        },

        async confirmDeleteAccount() {
            this.confirmDeleteOpen = false
            this.working = true
            this.setActionStatus('deleteAccount', 'working', 'Deleting…')
            try {
                const res = await authedFetch('/api/account/delete', {
                    method: 'DELETE',
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                clearAuth()
                this.$router.push('/login')
            } catch (e) {
                this.setActionStatus('deleteAccount', 'error', this.formatFailure('Delete account', e))
            } finally {
                this.working = false
            }
        },
    },
}
</script>

<style scoped src="./css/Settings.css"></style>