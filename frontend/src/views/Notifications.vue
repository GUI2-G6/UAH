<template>
    <div class="page">
        <div class="greeting">
            <h1>Notifications</h1>
            <p>Review recent update signals across your connected tracking feeds.</p>
        </div>
        <div class="dashboard">
            <Card class="notifications-card notifications-card--wide">
                <h2>Notifications Feed</h2>
                <p v-if="loading">Loading latest updates...</p>
                <p v-else-if="!gmailConnected">
                    Connect Gmail in Settings to enable status updates.
                    <button class="submit-btn" type="button" @click="$router.push('/settings')">Open Settings</button>
                </p>
                <p v-else-if="error">{{ error }}</p>
                <p v-else-if="summary.total === 0">No job updates found yet.</p>
                <p v-else>Latest job update feed ({{ summary.total }} total)</p>
                <p v-if="lastRefreshed" class="scan-meta">Last scan: {{ formatTimestamp(lastRefreshed) }}</p>
                <p v-if="submittedSessionCount !== null" class="scan-meta">Saved sessions available for analytics: {{ submittedSessionCount }}</p>
            </Card>
            <Card class="notifications-card">
                <h2>Total Pending: {{ summary.total }}</h2>
            </Card>
            <Card class="notifications-card">
                <h2>Action Required: {{ summary.action_required }}</h2>
            </Card>
            <Card class="notifications-card">
                <h2>Upcoming: {{ summary.upcoming }}</h2>
            </Card>
            <Card class="notifications-card notifications-card--wide">
                <template v-if="visibleResults.length">
                    <article v-for="(item, index) in visibleResults.slice(0, 8)" :key="`${item.source_id || item.subject}-${index}`" class="gmail-update-row">
                        <h3>{{ item.company_hint || 'Unknown company' }}</h3>
                        <p class="status-line">{{ item.detected_status }}</p>
                        <p>{{ item.subject || 'No subject' }}</p>
                        <p class="meta-line">{{ item.from }}</p>
                        <p class="meta-line">{{ formatTimestamp(item.date) }}</p>
                        <div class="notification-actions">
                            <button class="submit-btn" type="button" @click="snoozeItem(item)" :disabled="busyBySourceId[item.source_id] === true">Snooze 3 days</button>
                            <button class="submit-btn is-danger" type="button" @click="dismissItem(item)" :disabled="busyBySourceId[item.source_id] === true">Dismiss permanently</button>
                        </div>
                    </article>
                </template>
                <p v-else class="empty-feed">No scan entries yet.</p>
            </Card>
        </div>
    </div>
</template>

<script>
    import Card from '@/components/Card.vue';
    import { getCurrentUser } from '@/lib/auth.js'
    import {
        readGmailScanCache,
        resolveGmailConnectionStatus,
        subscribeGmailUpdates,
        summarizeGmailResults,
        filterResultsByNotificationStates,
        listGmailNotificationStates,
        upsertGmailNotificationState,
    } from '@/lib/gmailUpdates.js'

    export default{
        name: "Notifications",
        components:{
            Card
        },
        data() {
            return {
                loading: false,
                error: '',
                results: [],
                summary: summarizeGmailResults([]),
                lastRefreshed: '',
                gmailConnected: false,
                unsubscribeUpdates: null,
                submittedSessionCount: null,
                notificationStates: [],
                busyBySourceId: {},
                onUserUpdated: null,
            }
        },
        async mounted() {
            this.onUserUpdated = async () => {
                await this.refreshGmailConnected()
            }
            window.addEventListener('uah-user-updated', this.onUserUpdated)
            this.gmailConnected = Boolean(getCurrentUser()?.gmail_refresh_token)
            await this.refreshGmailConnected()
            const cached = readGmailScanCache()
            if (cached) this.applyScanRecord(cached)
            this.unsubscribeUpdates = subscribeGmailUpdates((record) => {
                this.applyScanRecord(record)
            })
            await this.loadNotificationStates()
        },
        beforeUnmount() {
            if (typeof this.unsubscribeUpdates === 'function') {
                this.unsubscribeUpdates()
            }
            if (this.onUserUpdated) {
                window.removeEventListener('uah-user-updated', this.onUserUpdated)
            }
        },
        computed: {
            visibleResults() {
                return filterResultsByNotificationStates(this.results, this.notificationStates)
            },
        },
        methods: {
            async refreshGmailConnected(force = false) {
                this.gmailConnected = await resolveGmailConnectionStatus(this.gmailConnected, { force })
            },
            async loadNotificationStates() {
                try {
                    this.notificationStates = await listGmailNotificationStates()
                    this.summary = summarizeGmailResults(this.visibleResults)
                } catch (err) {
                    this.error = String(err?.message || 'Unable to load notification settings.')
                }
            },
            applyScanRecord(record = {}) {
                const items = Array.isArray(record.results) ? record.results : []
                this.results = items
                this.summary = summarizeGmailResults(this.visibleResults)
                this.lastRefreshed = record.fetched_at || this.lastRefreshed
                this.submittedSessionCount = Number.isFinite(Number(record?.scan_scope?.applied_job_candidates))
                    ? Number(record.scan_scope.applied_job_candidates)
                    : null
                this.error = ''
            },
            async setItemState(item, action) {
                const sourceId = String(item?.source_id || '').trim()
                if (!sourceId) {
                    this.error = 'Missing source id for this notification.'
                    return
                }
                const previous = this.notificationStates.slice()
                const nextEntry = { source_id: sourceId, state: action === 'dismiss' ? 'dismissed' : 'snoozed', snoozed_until: '' }
                this.notificationStates = [
                    nextEntry,
                    ...previous.filter((row) => String(row?.source_id || '') !== sourceId),
                ]
                this.summary = summarizeGmailResults(this.visibleResults)
                this.busyBySourceId = { ...this.busyBySourceId, [sourceId]: true }
                try {
                    const saved = await upsertGmailNotificationState({ source_id: sourceId, action })
                    this.notificationStates = [
                        saved,
                        ...this.notificationStates.filter((row) => String(row?.source_id || '') !== sourceId),
                    ]
                    this.summary = summarizeGmailResults(this.visibleResults)
                } catch (err) {
                    this.notificationStates = previous
                    this.summary = summarizeGmailResults(this.visibleResults)
                    this.error = String(err?.message || 'Unable to update notification state.')
                } finally {
                    this.busyBySourceId = { ...this.busyBySourceId, [sourceId]: false }
                }
            },
            async snoozeItem(item) {
                await this.setItemState(item, 'snooze')
            },
            async dismissItem(item) {
                await this.setItemState(item, 'dismiss')
            },
            formatTimestamp(value) {
                if (!value) return 'Unknown date'
                const date = new Date(value)
                return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
            },
        },
    }
</script>

<style scoped src="./css/Notifications.css"></style>
