<template>
    <div class="greeting">
        <h1>Analytics</h1>
    </div>
    <!--Example Chart-->
    <Card>
        <Line :data="lineData" :options="lineOptions" />
    </Card>
    <Card>
        <Bar :data="barData" />
    </Card>
    <Card>
        <Pie :data="pieData" />
    </Card>
    <Card>
        <Doughnut :data="doughnutData" />
    </Card>
    <Card>
        <Radar :data="radarData" />
    </Card>
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
            return {
                lineData: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr'],
                    datasets: [
                        {
                            label: 'Users',
                            data: [10, 25, 18, 40],
                            borderColor: '#F7A8A8'
                        }
                    ]
                },
                lineOptions: {
                    responsive: true,
                    maintainAspectRatio: false
                },
                barData: {
                    labels: ['Jan', 'Feb', 'Mar'],
                    datasets: [
                    {
                        label: 'Sales',
                        data: [30, 50, 20],
                        backgroundColor: ['#F7A8A8', '#A8C5F7', '#A8F7C5'],

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
                            '#FCA5A5',
                            '#93C5FD',
                            '#86EFAC'
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
                            '#FCA5A5',
                            '#93C5FD',
                            '#86EFAC'
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
                        backgroundColor: 'rgba(99, 102, 241, 0.2)',
                        borderColor: '#6366F1',
                        pointBackgroundColor: '#6366F1'
                        }
                    ]
                },
            }
        }
    }
</script>

<style scoped src="./css/Placeholder.css"></style>