<template>
    <div class="page">
        <div class="greeting">
            <h1>Settings</h1>
        </div>
        <div class="dashboard">
            <Card class="settings-card settings-card--profile">
                <template #header>
                    <h3>Profile Settings</h3>
                </template>
                <div class="settings-group">
                    <p v-if="currentUser" class="signed-in">
                        Signed in as: <strong>{{ currentUser.email || 'Not set' }}</strong>
                    </p>
                    <p v-if="currentUser && currentUser.email" class="email-status" :class="{ 'is-verified': !!currentUser.email_verified }">
                        Email status: <strong>{{ currentUser.email_verified ? 'Verified' : 'Not verified' }}</strong>
                    </p>
                    <p v-if="currentUser" class="current-value">
                        Current name: <strong>{{ (currentUser.first_name || currentUser.firstName || '') + (currentUser.last_name || currentUser.lastName ? ' ' + (currentUser.last_name || currentUser.lastName) : '') || 'Not set' }}</strong>
                    </p>
                    <p>First Name</p>
                    <input id="settings-first-name" name="first_name" type="text" v-model="firstName" autocomplete="off">
                    <p>Last Name</p>
                    <input id="settings-last-name" name="last_name" type="text" v-model="lastName" autocomplete="off">
                    <button @click="changeName" :disabled="working" :class="buttonStatusClass('changeName')">Update name</button>
                    <div v-if="actionStatus.changeName.message" :class="feedbackClass('changeName')">
                        {{ actionStatus.changeName.message }}
                    </div>
                </div>
                <div class="settings-group">
                    <h4>Notifications & Preferences</h4>
                    <p class="current-value">These preferences are currently local to this browser session and are organized here for future account-level settings support.</p>
                    <p>Email Notifications</p>
                    <select v-model="emailNotifications" name="email_notifications" id="settings-email-notifications" autocomplete="off">
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                    </select>
                    <p>Reminder Notifications</p>
                    <select v-model="reminderNotifications" name="reminder_notifications" id="settings-reminder-notifications" autocomplete="off">
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                    </select>
                    <p>Application Status Updates</p>
                    <select v-model="applicationStatusUpdates" name="application_status_updates" id="settings-application-status-updates" autocomplete="off">
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                    </select>
                    <p>Language</p>
                    <select v-model="language" name="language" id="settings-language" autocomplete="off">
                        <option value="en">English</option>
                        <option value="es">Spanish</option>
                        <option value="fr">French</option>
                    </select>
                    <p>Timezone</p>
                    <select v-model="timezone" name="timezone" id="settings-timezone" autocomplete="off">
                        <option value="EST">Eastern Standard Time (EST)</option>
                        <option value="CST">Central Standard Time (CST)</option>
                        <option value="MST">Mountain Standard Time (MST)</option>
                        <option value="PST">Pacific Standard Time (PST)</option>
                    </select>
                </div>
            </Card>
            <Card class="settings-card settings-card--security">
                <template #header>
                    <h3>Account & Security</h3>
                </template>
                <div class="settings-group">
                    <h4>Change Email</h4>
                    <p v-if="currentUser" class="current-value">Current: <strong>{{ currentUser.email || 'Not set' }}</strong></p>
                    <form @submit.prevent="changeEmail" class="account-security-form">
                        <input
                            v-if="currentUser && currentUser.email"
                            class="credential-context"
                            type="email"
                            :value="currentUser.email"
                            autocomplete="username"
                            name="username"
                            readonly
                            tabindex="-1"
                            aria-hidden="true"
                        >
                        <input id="settings-new-email" name="username" type="email" v-model="changeEmailNew" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" placeholder="New email">
                        <input id="settings-new-email-confirm" name="confirm_new_email" type="email" v-model="changeEmailNewConfirm" autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false" placeholder="Confirm new email">
                        <button type="submit" :disabled="working" :class="buttonStatusClass('changeEmail')">Update email</button>
                    </form>
                    <div v-if="actionStatus.changeEmail.message" :class="feedbackClass('changeEmail')">
                        {{ actionStatus.changeEmail.message }}
                    </div>
                </div>

                <div class="settings-group">
                    <h4>Change Password</h4>
                    <form @submit.prevent="changePassword" class="account-security-form" autocomplete="off">
                        <input
                            v-if="currentUser && currentUser.email"
                            class="credential-context"
                            type="email"
                            :value="currentUser.email"
                            autocomplete="username"
                            name="username"
                            readonly
                            tabindex="-1"
                            aria-hidden="true"
                        >
                        <SecretInput id="settings-current-password" name="current_password" v-model="currentPassword" placeholder="Current password" autocomplete="off" :blockAutofill="true" inputmode="text" autocapitalize="none" autocorrect="off" :spellcheck="false" :disabled="working" />
                        <SecretInput id="settings-new-password" name="new_password" v-model="newPassword" placeholder="New password" autocomplete="off" :blockAutofill="true" inputmode="text" autocapitalize="none" autocorrect="off" :spellcheck="false" :disabled="working" />
                        <SecretInput id="settings-confirm-new-password" name="confirm_new_password" v-model="confirmNewPassword" placeholder="Confirm new password" autocomplete="off" :blockAutofill="true" inputmode="text" autocapitalize="none" autocorrect="off" :spellcheck="false" :disabled="working" />
                        <button type="submit" :disabled="working" :class="buttonStatusClass('changePassword')">Update password</button>
                    </form>
                    <div v-if="actionStatus.changePassword.message" :class="feedbackClass('changePassword')">
                        {{ actionStatus.changePassword.message }}
                    </div>
                </div>

                <div class="settings-group">
                    <h4>Email Verification</h4>
                    <form @submit.prevent="sendVerification" class="account-security-form">
                        <button type="submit" :disabled="working" :class="buttonStatusClass('sendVerification')">Send verification link</button>
                    </form>
                    <div v-if="actionStatus.sendVerification.message" :class="feedbackClass('sendVerification')">
                        {{ actionStatus.sendVerification.message }}
                    </div>
                    <form @submit.prevent="verifyEmail" class="account-security-form">
                        <SecretInput id="settings-email-verification-token" name="email_verification_token" v-model="verifyToken" placeholder="Verification token (manual fallback)" autocomplete="one-time-code" inputmode="text" autocapitalize="none" autocorrect="off" :spellcheck="false" :disabled="working" />
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
            <Card class="settings-card settings-card--integrations">
                <template #header>
                    <h3>Sign-in Methods</h3>
                </template>
                <div class="settings-group connected-accounts-group">
                    <p class="connected-accounts-intro">
                        After you create your account, you can optionally connect Google here and use Google to
                        sign in later. Manage linked sign-in providers separately from optional platform services
                        like Gmail updates.
                    </p>
                    <p v-if="connectedAccountsError" class="account-error">{{ connectedAccountsError }}</p>
                    <div class="connected-accounts-list">
                        <div class="connected-account-row" v-for="provider in connectedAccounts" :key="provider.provider">
                            <div class="connected-account-meta">
                                <p class="connected-account-title">
                                    {{ provider.label }}
                                    <span
                                        class="connected-account-badge"
                                        :class="provider.connected ? 'is-connected' : (provider.coming_soon ? 'is-coming-soon' : 'is-not-connected')"
                                    >
                                        {{ provider.connected ? 'Connected' : (provider.coming_soon ? 'Coming soon' : 'Not connected') }}
                                    </span>
                                </p>
                                <p v-if="provider.connected && provider.account_email" class="connected-account-detail">
                                    {{ provider.account_email }}
                                </p>
                                <p v-else-if="provider.disconnect_disabled_reason" class="connected-account-detail">
                                    {{ provider.disconnect_disabled_reason }}
                                </p>
                                <p v-else-if="provider.coming_soon" class="connected-account-detail">
                                    Provider support is planned.
                                </p>
                            </div>
                            <div class="connected-account-actions">
                                <button
                                    v-if="provider.connected"
                                    type="button"
                                    :disabled="connectedAccountsBusyProvider === provider.provider || !provider.can_disconnect"
                                    @click="disconnectProvider(provider.provider)"
                                >
                                    {{ connectedAccountsBusyProvider === provider.provider ? 'Disconnecting…' : 'Disconnect' }}
                                </button>
                                <button
                                    v-else
                                    type="button"
                                    :disabled="connectedAccountsBusyProvider === provider.provider || provider.coming_soon || !provider.can_connect"
                                    @click="connectProvider(provider.provider)"
                                >
                                    {{ connectedAccountsBusyProvider === provider.provider ? 'Connecting…' : 'Connect' }}
                                </button>
                            </div>
                        </div>
                    </div>
                    <button type="button" @click="loadConnectedAccounts" :disabled="connectedAccountsLoading || !!connectedAccountsBusyProvider">
                        {{ connectedAccountsLoading ? 'Refreshing…' : 'Refresh sign-in methods' }}
                    </button>
                </div>
                <div v-if="canAccessDebugTools" class="settings-group developer-tools-group">
                    <h4>Developer Tools</h4>
                    <p class="connected-accounts-intro">Dev only. Debug views and internal diagnostics stay hidden for normal accounts.</p>
                    <p class="developer-tools-capability">
                        Capability
                        <span class="connected-account-badge is-connected">Developer account</span>
                    </p>
                    <label class="developer-tools-toggle" for="settings-debug-tools-toggle">
                        <span>Show debug tools in this browser</span>
                        <input
                            id="settings-debug-tools-toggle"
                            type="checkbox"
                            :checked="showDebugTools"
                            @change="toggleDebugTools($event.target.checked)"
                        >
                    </label>
                    <p class="connected-account-detail">This toggle is local to this browser and can be turned off later without changing your account role.</p>
                </div>
            </Card>

            <Card class="settings-card settings-card--services">
                <template #header>
                    <h3>Service Connections</h3>
                </template>
                <div class="settings-group service-connections-group">
                    <p class="service-connections-intro">
                        Opt in to services that help UAH organize updates, reminders, and documents.
                    </p>
                    <p v-if="serviceConnectionsError" class="account-error">{{ serviceConnectionsError }}</p>
                    <div class="service-connections-list">
                        <div
                            v-for="service in serviceConnections"
                            :key="service.key"
                            class="service-connection-row"
                            :class="[
                                `is-${serviceClassKey(service.key)}`,
                                { 'is-highlighted': highlightedServiceKey === service.key },
                            ]"
                        >
                            <div class="service-connection-leading">
                                <div class="service-connection-chip" :class="`is-${serviceClassKey(service.key)}`">
                                    {{ serviceMonogram(service.key) }}
                                </div>
                                <div class="service-connection-meta">
                                    <p class="service-connection-title">
                                        {{ service.label }}
                                        <span class="connected-account-badge service-connection-badge" :class="serviceBadgeClass(service.status)">
                                            {{ serviceStatusLabel(service.status) }}
                                        </span>
                                    </p>
                                    <p class="service-connection-summary">{{ service.summary }}</p>
                                    <p v-if="service.account_label" class="service-connection-detail">{{ service.account_label }}</p>
                                </div>
                            </div>
                            <div class="service-connection-actions">
                                <button
                                    type="button"
                                    class="service-action-button"
                                    :class="`is-${service.primary_action?.style || 'secondary'}`"
                                    :disabled="serviceActionBusyKey === serviceBusyKey(service.key, service.primary_action?.key) || !service.primary_action?.enabled"
                                    @click="runServiceAction(service.primary_action, service.key)"
                                >
                                    {{ serviceActionLabel(service.primary_action, service.key) }}
                                </button>
                                <button
                                    type="button"
                                    class="service-action-button is-ghost"
                                    :disabled="serviceDetailsLoading && activeServiceDetails?.key === service.key"
                                    @click="openServiceDetails(service)"
                                >
                                    View Details
                                </button>
                            </div>
                        </div>
                    </div>
                    <button type="button" @click="loadServiceConnections" :disabled="serviceConnectionsLoading || !!serviceActionBusyKey">
                        {{ serviceConnectionsLoading ? 'Refreshing…' : 'Refresh services' }}
                    </button>
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

        <ServiceDetailsModal
            v-if="serviceDetailsOpen"
            :service="activeServiceDetails"
            :loading="serviceDetailsLoading"
            :error="serviceDetailsError"
            :busyActionKey="serviceActionBusyKey"
            @close="closeServiceDetails"
            @action="runServiceAction($event, activeServiceDetails?.key)"
        />
    </div>

</template>

<script>
import Card from "../components/Card.vue";
import ConfirmModal from "../components/ConfirmModal.vue";
import SecretInput from "../components/SecretInput.vue";
import ServiceDetailsModal from "../components/ServiceDetailsModal.vue";
import { authedFetch, clearAuth, getCurrentUser, setCurrentUser, syncCurrentUser } from "../lib/auth.js";
import { setDebugToolsPreference, subscribeDebugTools } from "../lib/debugTools.js";
import { assertValidEmail } from "../lib/validation.js";
import { showToast } from '@/services/toastService.js';

const SERVICE_STATUS_LABELS = {
    connected: 'Connected',
    available: 'Available',
    coming_soon: 'Coming soon',
    needs_attention: 'Needs attention',
}

const SERVICE_MONOGRAMS = {
    gmail: 'GM',
    calendar_sync: 'CS',
    resume_imports: 'RI',
}

export default {
  name: "Settings",
  components: {
        Card,
        ConfirmModal,
        SecretInput,
        ServiceDetailsModal,
    },
    data() {
        return {
            currentUser: null,
            firstName: '',
            lastName: '',

            working: false,
            actionStatus: {
                changeName: { state: 'idle', message: '' },
                changeEmail: { state: 'idle', message: '' },
                changePassword: { state: 'idle', message: '' },
                sendVerification: { state: 'idle', message: '' },
                verifyEmail: { state: 'idle', message: '' },
                deleteAccount: { state: 'idle', message: '' },
            },
            _actionTimers: {},
            _serviceHighlightTimer: null,

            changeEmailNew: '',
            changeEmailNewConfirm: '',

            currentPassword: '',
            newPassword: '',
            confirmNewPassword: '',

            verifyToken: '',

            confirmDeleteOpen: false,

            connectedAccounts: [],
            connectedAccountsLoading: false,
            connectedAccountsError: '',
            connectedAccountsBusyProvider: '',

            serviceConnections: [],
            serviceConnectionsLoading: false,
            serviceConnectionsError: '',
            serviceActionBusyKey: '',
            serviceDetailsOpen: false,
            serviceDetailsLoading: false,
            serviceDetailsError: '',
            activeServiceDetails: null,
            highlightedServiceKey: '',

            emailNotifications: 'yes',
            reminderNotifications: 'yes',
            applicationStatusUpdates: 'yes',
            language: 'en',
            timezone: 'EST',

            canAccessDebugTools: false,
            showDebugTools: false,
            debugToolsUnsubscribe: null,
        }
    },
    async mounted() {
        await this.loadUser()
        await Promise.all([
            this.loadConnectedAccounts(),
            this.loadServiceConnections(),
        ])
        this.handleConnectedAccountRedirectState()
        this.handleServiceRedirectState()
        this.handleEmailVerificationRedirectState()
        this.debugToolsUnsubscribe = subscribeDebugTools((state) => {
            this.canAccessDebugTools = state.canAccessDebugTools === true
            this.showDebugTools = state.showDebugTools === true
        })
    },
    beforeUnmount() {
        if (typeof this.debugToolsUnsubscribe === 'function') {
            this.debugToolsUnsubscribe()
        }
        Object.values(this._actionTimers).forEach((timer) => {
            if (timer) clearTimeout(timer)
        })
        if (this._serviceHighlightTimer) {
            clearTimeout(this._serviceHighlightTimer)
            this._serviceHighlightTimer = null
        }
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
        toggleDebugTools(enabled) {
            const nextState = setDebugToolsPreference(enabled === true, this.currentUser)
            this.canAccessDebugTools = nextState.canAccessDebugTools === true
            this.showDebugTools = nextState.showDebugTools === true

            if (!this.showDebugTools && this.$route?.meta?.debugOnly) {
                this.$router.replace('/home')
            }
        },
        serviceClassKey(key) {
            return String(key || 'service').trim().toLowerCase().replaceAll('_', '-')
        },
        serviceMonogram(key) {
            return SERVICE_MONOGRAMS[key] || 'SV'
        },
        serviceStatusLabel(status) {
            return SERVICE_STATUS_LABELS[status] || 'Available'
        },
        serviceBadgeClass(status) {
            if (status === 'connected') return 'is-connected'
            if (status === 'coming_soon') return 'is-coming-soon'
            if (status === 'needs_attention') return 'is-needs-attention'
            return 'is-available'
        },
        serviceBusyKey(serviceKey, actionKey) {
            return `${serviceKey || ''}:${actionKey || ''}`
        },
        serviceActionLabel(action, serviceKey) {
            if (!action) return 'Unavailable'
            const busyKey = this.serviceBusyKey(serviceKey, action.key)
            if (this.serviceActionBusyKey !== busyKey) return action.label
            if (action.key === 'connect') return 'Connecting…'
            if (action.key === 'disconnect') return 'Disconnecting…'
            return 'Working…'
        },
        setServiceHighlight(serviceKey) {
            this.highlightedServiceKey = serviceKey || ''
            if (this._serviceHighlightTimer) {
                clearTimeout(this._serviceHighlightTimer)
                this._serviceHighlightTimer = null
            }
            if (!serviceKey) return
            this._serviceHighlightTimer = setTimeout(() => {
                this.highlightedServiceKey = ''
                this._serviceHighlightTimer = null
            }, 4200)
        },
        handleConnectedAccountRedirectState() {
            const accountsState = typeof this.$route?.query?.accounts === 'string' ? this.$route.query.accounts : ''
            const provider = typeof this.$route?.query?.provider === 'string' ? this.$route.query.provider : ''
            const reason = typeof this.$route?.query?.reason === 'string' ? this.$route.query.reason : ''

            if (!accountsState) return

            if (accountsState === 'connected') {
                showToast(`${provider || 'Account'} connected successfully`, 'success')
            } else if (accountsState === 'error') {
                const detail = reason ? ` (${reason.replaceAll('_', ' ')})` : ''
                showToast(`Could not connect ${provider || 'account'}${detail}`, 'error')
            }

            const nextQuery = { ...this.$route.query }
            delete nextQuery.accounts
            delete nextQuery.provider
            delete nextQuery.reason
            this.$router.replace({ path: this.$route.path, query: nextQuery })
        },
        handleServiceRedirectState() {
            const serviceKey = typeof this.$route?.query?.service === 'string' ? this.$route.query.service : ''
            const serviceState = typeof this.$route?.query?.service_state === 'string' ? this.$route.query.service_state : ''
            const reason = typeof this.$route?.query?.service_reason === 'string' ? this.$route.query.service_reason : ''

            if (!serviceKey || !serviceState) return

            const serviceSummary = this.serviceConnections.find((item) => item.key === serviceKey)
            const serviceLabel = serviceSummary?.label || 'Service'

            if (serviceState === 'connected') {
                showToast(`${serviceLabel} connected`, 'success')
            } else if (serviceState === 'disconnected') {
                showToast(`${serviceLabel} disconnected`, 'success')
            } else if (serviceState === 'error') {
                const detail = reason ? ` (${reason.replaceAll('_', ' ')})` : ''
                showToast(`Could not update ${serviceLabel}${detail}`, 'error')
            }

            this.setServiceHighlight(serviceKey)

            const nextQuery = { ...this.$route.query }
            delete nextQuery.service
            delete nextQuery.service_state
            delete nextQuery.service_reason
            this.$router.replace({ path: this.$route.path, query: nextQuery })
        },
        handleEmailVerificationRedirectState() {
            const verifyState = typeof this.$route?.query?.verify_email === 'string' ? this.$route.query.verify_email : ''
            const reason = typeof this.$route?.query?.verify_reason === 'string' ? this.$route.query.verify_reason : ''

            if (!verifyState) return

            if (verifyState === 'success') {
                showToast('Email verified successfully', 'success')
            } else if (verifyState === 'error') {
                const detail = reason ? ` (${reason.replaceAll('_', ' ')})` : ''
                showToast(`Could not verify email${detail}`, 'error')
            }

            const nextQuery = { ...this.$route.query }
            delete nextQuery.verify_email
            delete nextQuery.verify_reason
            this.$router.replace({ path: this.$route.path, query: nextQuery })
        },
        async loadConnectedAccounts() {
            this.connectedAccountsLoading = true
            this.connectedAccountsError = ''
            try {
                const res = await authedFetch('/api/auth/connected-accounts')
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                this.connectedAccounts = Array.isArray(data?.providers) ? data.providers : []
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated') {
                    this.$router.push('/login')
                    return
                }
                this.connectedAccountsError = this.formatFailure('Load connected accounts', e)
            } finally {
                this.connectedAccountsLoading = false
            }
        },
        async loadServiceConnections() {
            this.serviceConnectionsLoading = true
            this.serviceConnectionsError = ''
            try {
                const res = await authedFetch('/api/integrations/services')
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                this.serviceConnections = Array.isArray(data) ? data : []
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated') {
                    this.$router.push('/login')
                    return
                }
                this.serviceConnectionsError = this.formatFailure('Load services', e)
            } finally {
                this.serviceConnectionsLoading = false
            }
        },
        async connectProvider(provider) {
            if (provider !== 'google') return

            this.connectedAccountsBusyProvider = provider
            this.connectedAccountsError = ''
            try {
                const res = await authedFetch('/api/auth/google/connect/start', {
                    method: 'POST',
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                if (!data?.authorization_url) throw new Error('Missing authorization URL')
                window.location.assign(data.authorization_url)
            } catch (e) {
                const msg = this.formatFailure('Connect Google', e)
                this.connectedAccountsError = msg
                showToast(msg, 'error')
                this.connectedAccountsBusyProvider = ''
            }
        },
        async disconnectProvider(provider) {
            if (provider !== 'google') return

            this.connectedAccountsBusyProvider = provider
            this.connectedAccountsError = ''
            try {
                const res = await authedFetch('/api/auth/google/disconnect', {
                    method: 'DELETE',
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                showToast(data?.message || 'Google account disconnected', 'success')
                await this.loadConnectedAccounts()
                await this.loadUser()
            } catch (e) {
                const msg = this.formatFailure('Disconnect Google', e)
                this.connectedAccountsError = msg
                showToast(msg, 'error')
            } finally {
                this.connectedAccountsBusyProvider = ''
            }
        },
        primeServiceDetails(service) {
            if (!service) {
                this.activeServiceDetails = null
                return
            }
            this.activeServiceDetails = {
                key: service.key,
                label: service.label,
                status: service.status,
                connected: service.connected,
                account_label: service.account_label,
                availability: service.availability,
                description: service.summary,
                capabilities: [],
                permissions: [],
                readiness: {
                    title: 'Loading details…',
                    description: 'Fetching service details for this connection.',
                    tone: 'neutral',
                },
                planned_features: [],
                actions: service.primary_action ? [service.primary_action] : [],
            }
        },
        async openServiceDetails(service) {
            this.serviceDetailsOpen = true
            this.serviceDetailsError = ''
            this.primeServiceDetails(service)
            await this.loadServiceDetails(service?.key)
        },
        closeServiceDetails() {
            this.serviceDetailsOpen = false
            this.serviceDetailsLoading = false
            this.serviceDetailsError = ''
            this.activeServiceDetails = null
        },
        async loadServiceDetails(serviceKey) {
            if (!serviceKey) return

            this.serviceDetailsLoading = true
            this.serviceDetailsError = ''
            try {
                const res = await authedFetch(`/api/integrations/services/${serviceKey}`)
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                this.activeServiceDetails = data
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated') {
                    this.$router.push('/login')
                    return
                }
                this.serviceDetailsError = this.formatFailure('Load service details', e)
            } finally {
                this.serviceDetailsLoading = false
            }
        },
        async runServiceAction(action, serviceKey) {
            if (!action || !serviceKey || !action.enabled || !action.href) return

            const busyKey = this.serviceBusyKey(serviceKey, action.key)
            this.serviceActionBusyKey = busyKey
            this.serviceConnectionsError = ''
            if (this.activeServiceDetails?.key === serviceKey) {
                this.serviceDetailsError = ''
            }

            try {
                const res = await authedFetch(action.href, {
                    method: action.method || 'POST',
                })
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)

                if (action.key === 'connect') {
                    if (!data?.authorization_url) {
                        throw new Error('Missing authorization URL')
                    }
                    window.location.assign(data.authorization_url)
                    return
                }

                const label = this.activeServiceDetails?.label || this.serviceConnections.find((item) => item.key === serviceKey)?.label || 'Service'
                showToast(data?.message || `${label} updated`, 'success')
                await Promise.all([
                    this.loadServiceConnections(),
                    this.loadUser(),
                ])
                if (this.activeServiceDetails?.key === serviceKey) {
                    await this.loadServiceDetails(serviceKey)
                }
                this.setServiceHighlight(serviceKey)
            } catch (e) {
                const msg = this.formatFailure(`${action.label} service`, e)
                if (this.activeServiceDetails?.key === serviceKey) {
                    this.serviceDetailsError = msg
                }
                this.serviceConnectionsError = msg
                showToast(msg, 'error')
            } finally {
                this.serviceActionBusyKey = ''
            }
        },
        async loadUser() {
            this.currentUser = getCurrentUser()

            if (this.currentUser) {
                this.firstName = this.currentUser.first_name || this.currentUser.firstName || ''
                this.lastName = this.currentUser.last_name || this.currentUser.lastName || ''
            }

            try {
                const user = await syncCurrentUser({ force: true })
                if (!user) {
                    this.$router.push('/login')
                    return
                }
                this.currentUser = user

                this.firstName = user.first_name || user.firstName || this.firstName
                this.lastName = user.last_name || user.lastName || this.lastName
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated' || e.message === 'HTTP 401') {
                    this.$router.push('/login')
                }
                // otherwise ignore (backend may be down)
            }
        },

        async changeName() {
            const emptyField = !this.firstName || !this.lastName
            if (emptyField) {
                showToast('Please fill out all required fields', 'error');
                return;
            }

            this.working = true
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
                showToast('Name updated successfully!', 'success');
            } catch (e) {
                showToast('Failed to update name: ' + e.message, 'error');
            } finally {
                this.working = false
            }
        },

        async changePassword() {
            if (!this.newPassword || !this.confirmNewPassword) {
                showToast('Please enter and confirm your new password', 'error')
                return
            }
            if (this.newPassword !== this.confirmNewPassword) {
                showToast('New passwords do not match', 'error')
                return
            }
            this.working = true
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
                showToast('Password changed successfully', 'success')
                this.currentPassword = ''
                this.newPassword = ''
                this.confirmNewPassword = ''
            } catch (e) {
                showToast('Failed to update password:' + e.message, 'error')
            } finally {
                this.working = false
            }
        },

        async changeEmail() {
            let newEmail = ''
            let newEmailConfirm = ''
            try {
                newEmail = assertValidEmail(this.changeEmailNew, 'new email')
                newEmailConfirm = assertValidEmail(this.changeEmailNewConfirm, 'confirm email')
            } catch (e) {
                const msg = e?.message ?? 'Please enter a valid email address'
                showToast(msg, 'error')
                return
            }
            if (!newEmail || !newEmailConfirm) {
                const msg = 'Please enter and confirm your new email'
                showToast(msg, 'error')
                return
            }
            if (newEmail.toLowerCase() !== newEmailConfirm.toLowerCase()) {
                const msg = 'Emails do not match'
                showToast(msg, 'error')
                return
            }
            this.working = true
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
                showToast(msg, 'error')
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
