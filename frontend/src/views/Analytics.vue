<template>
    <div class="greeting">
        <h1>Analytics</h1>
        <p v-if="lastUpdated">Last updated {{ lastUpdated }}</p>
    </div>
    <p v-if="loading" class="empty-state-copy">Loading analytics data...</p>
    <p v-else-if="error" class="empty-state-copy">{{ error }}</p>
    <div class="analytics-grid">
        <Card v-if="!loading && !error" class="analytics-card">
            <Line :data="lineData" :options="lineOptions" />
        </Card>
        <Card v-if="!loading && !error" class="analytics-card">
            <Bar :data="barData" :options="chartOptions" />
        </Card>
        <Card v-if="!loading && !error" class="analytics-card">
            <Pie :data="pieData" :options="chartOptions" />
        </Card>
        <Card v-if="!loading && !error" class="analytics-card">
            <Doughnut :data="doughnutData" :options="chartOptions" />
        </Card>
        <Card v-if="!loading && !error" class="analytics-card">
            <Radar :data="radarData" :options="radarOptions" />
        </Card>
    </div>
</template>

<script>
    import Card from '../components/Card.vue'
    import { authedFetch } from '../lib/auth.js'
    import { Line, Bar, Pie, Doughnut, Radar } from 'vue-chartjs'  // Default Chartjs charts.
    import {
        Chart as ChartJS,
        Title,
        Tooltip,
        Legend,
        LineElement,
        PointElement,
        CategoryScale,
        LinearScale,
        BarElement,
        ArcElement,
        RadialLinearScale
    } from 'chart.js'


    ChartJS.register(
        Title,
        Tooltip,
        Legend,
        LineElement,
        PointElement,
        CategoryScale,
        LinearScale,
        BarElement,
        ArcElement,
        RadialLinearScale
    )
    export default{
        name: "Analytics",
        components: {
            Card,
            Line,
            Bar,
            Pie,
            Doughnut,
            Radar,
        },
        data() {
            const css = getComputedStyle(document.documentElement)
            const text = css.getPropertyValue('--color-text-primary').trim() || '#e2e8f0'
            const muted = css.getPropertyValue('--color-text-muted').trim() || '#94a3b8'
            const grid = 'rgba(148, 163, 184, 0.22)'
            return {
                loading: false,
                error: '',
                lastUpdated: '',
                lineData: {
                    labels: ['Started', 'In Progress', 'Submitted', 'Abandoned'],
                    datasets: [
                        {
                            label: 'Apply sessions',
                            data: [0, 0, 0, 0],
                            borderColor: '#7cb6ff'
                        }
                    ]
                },
                lineOptions: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: text,
                            },
                        },
                    },
                    scales: {
                        x: { ticks: { color: muted }, grid: { color: grid } },
                        y: { ticks: { color: muted }, grid: { color: grid } },
                    },
                },
                chartOptions: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: text,
                            },
                        },
                    },
                },
                barData: {
                    labels: ['Tracked Active', 'Tracked with Updates', 'Stale Submissions'],
                    datasets: [
                    {
                        label: 'Tracking health',
                        data: [0, 0, 0],
                        backgroundColor: ['#fda4af', '#7cb6ff', '#86efac'],

                        borderRadius: {
                            topLeft: 10,
                            topRight: 10,
                            bottomLeft: 0,
                            bottomRight: 0
                        },
                    }
                    ]
                },
                pieData: {
                    labels: ['Started', 'In Progress', 'Submitted', 'Abandoned'],
                    datasets: [
                        {
                        data: [0, 0, 0, 0],
                        backgroundColor: [
                            '#fda4af',
                            '#7cb6ff',
                            '#86efac',
                            '#fbbf24'
                        ]
                        }
                    ]
                },
                doughnutData: {
                    labels: ['Last 7 days', 'Older events'],
                    datasets: [
                        {
                        data: [0, 0],
                        backgroundColor: [
                            '#fda4af',
                            '#7cb6ff'
                        ],
                        borderWidth: 0
                        }
                    ]
                },
                radarData: {
                    labels: ['Events', 'Tracked Active', 'Updates', 'Stale', 'Submitted'],
                    datasets: [
                        {
                        label: 'Account activity profile',
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: 'rgba(124, 182, 255, 0.25)',
                        borderColor: '#7cb6ff',
                        pointBackgroundColor: '#7cb6ff'
                        }
                    ]
                },
                radarOptions: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: text } },
                    },
                    scales: {
                        r: {
                            angleLines: { color: grid },
                            grid: { color: grid },
                            pointLabels: { color: muted },
                            ticks: { color: muted, backdropColor: 'transparent' },
                        },
                    },
                },
            }
        },
        async mounted() {
            await this.loadAnalytics()
        },
        methods: {
            async loadAnalytics() {
                this.loading = true
                this.error = ''
                try {
                    const res = await authedFetch('/api/apply-sessions/analytics/summary')
                    const data = await res.json().catch(() => null)
                    if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                    this.mapSummaryToCharts(data || {})
                    this.lastUpdated = this.formatTimestamp(data?.generated_at || new Date().toISOString())
                } catch (error) {
                    this.error = String(error?.message || 'Unable to load analytics')
                } finally {
                    this.loading = false
                }
            },
            mapSummaryToCharts(summary) {
                const statusCounts = summary?.status_counts || {}
                const started = Number(statusCounts.started || 0)
                const inProgress = Number(statusCounts.in_progress || 0)
                const submitted = Number(statusCounts.submitted || 0)
                const abandoned = Number(statusCounts.abandoned || 0)
                const trackedActive = Number(summary?.tracked_active_count || 0)
                const trackedUpdates = Number(summary?.tracked_updates_count || 0)
                const stale = Number(summary?.stale_submissions_count || 0)
                const totalEvents = Number(summary?.total_events || 0)
                const recentEvents = Number(summary?.event_counts_last_7_days || 0)
                const olderEvents = Math.max(0, totalEvents - recentEvents)

                this.lineData = {
                    ...this.lineData,
                    datasets: [{ ...this.lineData.datasets[0], data: [started, inProgress, submitted, abandoned] }],
                }
                this.barData = {
                    ...this.barData,
                    datasets: [{ ...this.barData.datasets[0], data: [trackedActive, trackedUpdates, stale] }],
                }
                this.pieData = {
                    ...this.pieData,
                    datasets: [{ ...this.pieData.datasets[0], data: [started, inProgress, submitted, abandoned] }],
                }
                this.doughnutData = {
                    ...this.doughnutData,
                    datasets: [{ ...this.doughnutData.datasets[0], data: [recentEvents, olderEvents] }],
                }
                this.radarData = {
                    ...this.radarData,
                    datasets: [{ ...this.radarData.datasets[0], data: [totalEvents, trackedActive, trackedUpdates, stale, submitted] }],
                }
            },
            formatTimestamp(value) {
                const parsed = new Date(value)
                return Number.isNaN(parsed.getTime()) ? 'Recently' : parsed.toLocaleString()
            },
        }
    }
</script>

<style scoped src="./css/Placeholder.css"></style>