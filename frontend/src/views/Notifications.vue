<template>
    <div class="page">
        <div class="greeting">
            <h1>Notifications</h1>
            <p>Keep track of ATS updates tied to jobs you actually applied to.</p>
        </div>
        <div class="dashboard">
            <Card class="notifications-card notifications-card--wide">
                <h2>Notifications Feed</h2>
                <p v-if="loading">Scanning Gmail updates...</p>
                <p v-else-if="!gmailConnected">Connect Gmail in Settings to enable status updates.</p>
                <p v-else-if="error">{{ error }}</p>
                <p v-else-if="summary.total === 0">No ATS updates matched your submitted applications yet.</p>
                <p v-else>Latest ATS update feed ({{ summary.matched_total }} matched, {{ summary.provisional_total }} provisional)</p>
                <p v-if="lastRefreshed" class="scan-meta">Last scan: {{ formatTimestamp(lastRefreshed) }}</p>
                <p v-if="submittedSessionCount !== null" class="scan-meta">Submitted sessions available for matching: {{ submittedSessionCount }}</p>
                <div class="actions">
                    <button class="submit-btn" type="button" :disabled="loading || !gmailConnected" @click="scanNow">
                        {{ loading ? 'Scanning…' : 'Run Gmail scan' }}
                    </button>
                </div>
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
                <template v-if="results.length">
                    <article v-for="(item, index) in results.slice(0, 8)" :key="`${item.subject}-${index}`" class="gmail-update-row">
                        <h3>{{ item.company_hint || 'Unknown company' }}</h3>
                        <p class="status-line">{{ item.detected_status }} · {{ item.tracking_source }} · {{ item.confidence }}</p>
                        <p>{{ item.subject || 'No subject' }}</p>
                        <p class="meta-line">{{ item.from }}</p>
                        <p class="meta-line">{{ formatTimestamp(item.date) }}</p>
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
    import { readGmailScanCache, runGmailScan, subscribeGmailUpdates, summarizeGmailResults } from '@/lib/gmailUpdates.js'

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
            }
        },
        async mounted() {
            this.gmailConnected = Boolean(getCurrentUser()?.gmail_refresh_token)
            const cached = readGmailScanCache()
            if (cached) this.applyScanRecord(cached)
            this.unsubscribeUpdates = subscribeGmailUpdates((record) => {
                this.applyScanRecord(record)
            })
        },
        beforeUnmount() {
            if (typeof this.unsubscribeUpdates === 'function') {
                this.unsubscribeUpdates()
            }
        },
        methods: {
            applyScanRecord(record = {}) {
                const items = Array.isArray(record.results) ? record.results : []
                this.results = items
                this.summary = summarizeGmailResults(items)
                this.lastRefreshed = record.fetched_at || this.lastRefreshed
                this.submittedSessionCount = Number.isFinite(Number(record?.scan_scope?.applied_job_candidates))
                    ? Number(record.scan_scope.applied_job_candidates)
                    : null
                this.error = ''
            },
            formatTimestamp(value) {
                if (!value) return 'Unknown date'
                const date = new Date(value)
                return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
            },
            async scanNow() {
                this.loading = true
                this.error = ''
                try {
                    const record = await runGmailScan()
                    this.applyScanRecord(record)
                    this.gmailConnected = true
                } catch (error) {
                    this.error = error?.message || 'Could not scan Gmail updates.'
                } finally {
                    this.loading = false
                }
            },
        },
    }
</script>

<style scoped src="./css/Notifications.css"></style>
