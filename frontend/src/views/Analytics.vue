<template>
    <div class="greeting">
        <h1>Analytics</h1>
    </div>
    <div class="analytics-grid">
        <Card class="analytics-card">
            <Line :data="lineData" :options="lineOptions" />
        </Card>
        <Card class="analytics-card">
            <Bar :data="barData" :options="chartOptions" />
        </Card>
        <Card class="analytics-card">
            <Pie :data="pieData" :options="chartOptions" />
        </Card>
        <Card class="analytics-card">
            <Doughnut :data="doughnutData" :options="chartOptions" />
        </Card>
        <Card class="analytics-card">
            <Radar :data="radarData" :options="radarOptions" />
        </Card>
    </div>
</template>

<script>
    import Card from '../components/Card.vue'
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
                lineData: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr'],
                    datasets: [
                        {
                            label: 'Users',
                            data: [10, 25, 18, 40],
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
                    labels: ['Jan', 'Feb', 'Mar'],
                    datasets: [
                    {
                        label: 'Sales',
                        data: [30, 50, 20],
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
                    labels: ['Red', 'Blue', 'Green'],
                    datasets: [
                        {
                        data: [30, 50, 20],
                        backgroundColor: [
                            '#fda4af',
                            '#7cb6ff',
                            '#86efac'
                        ]
                        }
                    ]
                },
                doughnutData: {
                    labels: ['Red', 'Blue', 'Green'],
                    datasets: [
                        {
                        data: [30, 50, 20],
                        backgroundColor: [
                            '#fda4af',
                            '#7cb6ff',
                            '#86efac'
                        ],
                        borderWidth: 0
                        }
                    ]
                },
                radarData: {
                    labels: ['Strength', 'Speed', 'Agility', 'Intelligence', 'Stamina'],
                    datasets: [
                        {
                        label: 'Player 1',
                        data: [80, 60, 70, 90, 75],
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
        }
    }
</script>

<style scoped src="./css/Placeholder.css"></style>