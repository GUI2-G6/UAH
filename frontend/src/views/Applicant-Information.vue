<template>
    <div class="page">
        <div class="greeting">
            <h1>Applicant Information</h1>
            <h2>Store your information for quick autofill in job applications</h2>
        </div>
        <div class="dashboard">
            <Card>                
                <template #header>
                    <h3>Personal Information</h3>
                </template>
                <div class="appInfo-group">
                    <p>First Name</p>
                    <input id="applicant-first-name" type="text" name="first_name" autocomplete="given-name" v-model="firstName">
                    <p>Last Name</p>
                    <input id="applicant-last-name" type="text" name="last_name" autocomplete="family-name" v-model="lastName">
                    <p>Email</p>
                    <input id="applicant-email" type="email" name="email" autocomplete="email" autocapitalize="none" autocorrect="off" spellcheck="false" v-model="currentUser.email">
                    <p>Phone</p>
                    <input id="applicant-phone" type="tel" name="phone" autocomplete="tel" v-model="currentUser.phone">
                    <p>LinkedIN URL</p>
                    <input id="applicant-linkedin-url" type="url" name="linkedin_url" autocomplete="url" autocapitalize="none" autocorrect="off" spellcheck="false" v-model="currentUser.linkedin">
                    <p>Portfolio/Website</p>
                    <input id="applicant-portfolio-url" type="url" name="portfolio_url" autocomplete="url" autocapitalize="none" autocorrect="off" spellcheck="false" v-model="currentUser.portfolio">
                </div>
            </Card>

            <Card>
                <template #header>
                    <h3>Address</h3>
                </template>
                <div class="appInfo-group">
                    <p>Street Address</p>
                    <input id="applicant-street-address" type="text" name="street_address" autocomplete="street-address" v-model="currentUser.streetAddress" placeholder="Street address">
                    <p>City</p>
                    <input id="applicant-city" type="text" name="city" autocomplete="address-level2" v-model="currentUser.city" placeholder="City">
                    <p>State/Province</p>
                    <input id="applicant-state" type="text" name="state" autocomplete="address-level1" v-model="currentUser.state" placeholder="State/Province">
                    <p>ZIP/Postal Code</p>
                    <input id="applicant-postal-code" type="text" name="postal_code" autocomplete="postal-code" inputmode="numeric" v-model="currentUser.zip" placeholder="ZIP/Postal Code">
                </div>
            </Card>

            <Card>
                <div class="appInfo-group">
                    <h3>Professional Summary</h3>
                    <span>Summary</span>
                    <p style="white-space: pre-line;">{{ message }}</p>
                    <textarea id="applicant-professional-summary" name="professional_summary" autocomplete="off" v-model="message" placeholder="Brief professional summary highlighting your key skills and experience..."></textarea>
                </div>
            </Card>

            <Card>
                <div class="appInfo-group">
                    <h3>Work Authorization</h3>
                    <p>Work Authorization Status</p>
                    <select name="authorization_status" id="authorization-status" autocomplete="off">
                        <option>US Citizen</option>
                        <option>Green Card Holder</option>
                        <option>H1-B Visa</option>
                        <option>OPT/CPT</option>
                        <option>Other</option>
                        <option>Require Sponsorship</option>
                    </select>
                    <p>Requires Sponsorship</p>
                    <select name="requires_sponsorship" id="requires-sponsorship" autocomplete="off">
                        <option>Yes</option>
                        <option>No</option>
                        <option>In the future</option>
                    </select>
                </div>
            </Card>


            <Card>
                <div class="appInfo-group">
                <h3>Education</h3>
                    <p>Degree</p>
                    <input id="applicant-degree" type="text" name="degree" autocomplete="organization-title" v-model="currentUser.degree" placeholder="Degree">
                    <p>Major/Field of Study</p>
                    <input id="applicant-major" type="text" name="major" autocomplete="off" v-model="currentUser.major" placeholder="Major/Field of Study">
                    <p>University</p>
                    <input id="applicant-university" type="text" name="university" autocomplete="organization" v-model="currentUser.university" placeholder="University">
                    <p>Graduation Year</p>
                    <input id="applicant-graduation-year" type="text" name="graduation_year" inputmode="numeric" autocomplete="off" v-model="currentUser.gradYear" placeholder="Graduation Year">
                    <p>GPA (Optional)</p>
                    <input id="applicant-gpa" type="text" name="gpa" inputmode="decimal" autocomplete="off" v-model="currentUser.gpa" placeholder="GPA">
                </div>
            </Card>

            <Card>
                <h3>Skills and Languages</h3>
            </Card>

            <Card>
                <h3>Current Experience</h3>
                <p>Years of Experience</p>
                <input id="applicant-years-experience" type="text" name="years_experience" inputmode="numeric" autocomplete="off" v-model="currentUser.yearsExperience" placeholder="Years of Experience">
                <p>Current Job Title</p>
                <input id="applicant-current-job-title" type="text" name="current_job_title" autocomplete="organization-title" v-model="currentUser.currentJobTitle" placeholder="Current Job Title">
                <p>Current Company</p>
                <input id="applicant-current-company" type="text" name="current_company" autocomplete="organization" v-model="currentUser.currentCompany" placeholder="Current Company">
            </Card>

            <Card>
                <h3>Job Preferences</h3>
                <p>Desired Salary Range</p>
                <input id="applicant-desired-salary-range" type="text" name="desired_salary_range" autocomplete="off" v-model="currentUser.salaryRange" placeholder="Desired Salary Range">
                <p>Preferred Job Locations</p>
                <input id="applicant-preferred-locations" type="text" name="preferred_locations" autocomplete="off" v-model="currentUser.preferredLocations" placeholder="Preferred Job Locations">
                <p>Remote Work Preference</p>
                <select name="remote_work_preference" id="remote-work-preference" autocomplete="off">
                    <option>Remote Only</option>
                    <option>On-site</option>
                    <option>Hybrid</option>
                    <option>No Preference</option>
                </select>
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
import { authedFetch, clearAuth, getCurrentUser, setCurrentUser } from "../lib/auth.js";

export default {
  name: "ApplicantInformation",
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
            this.currentUser = getCurrentUser()

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
                setCurrentUser(user)

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
            } catch (e) {
                this.setActionStatus('changeName', 'error', this.formatFailure('Update name', e))
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
                this.setActionStatus('changeEmail', 'error', 'Please enter and confirm your new email')
                return
            }
            if (newEmail.toLowerCase() !== newEmailConfirm.toLowerCase()) {
                this.setActionStatus('changeEmail', 'error', 'Emails do not match')
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
                this.setActionStatus('changeEmail', 'error', this.formatFailure('Update email', e))
            } finally {
                this.working = false
            }
        },

        async changeUsername() {
            const newUsername = (this.changeUsernameNew || '').trim()
            const newUsernameConfirm = (this.changeUsernameNewConfirm || '').trim()
            if (!newUsername || !newUsernameConfirm) {
                this.setActionStatus('changeUsername', 'error', 'Please enter and confirm your new username')
                return
            }
            if (newUsername !== newUsernameConfirm) {
                this.setActionStatus('changeUsername', 'error', 'Usernames do not match')
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
                this.changeUsernameNewConfirm = ''
            } catch (e) {
                this.setActionStatus('changeUsername', 'error', this.formatFailure('Update username', e))
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
