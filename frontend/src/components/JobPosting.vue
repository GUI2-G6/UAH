<template>
    <Card>
        <template #header>
            <h3>{{ job.title }}</h3>
        </template>
        <p>{{ job.company }}</p>
        <p>{{ job.location }}</p>
        <button @click="apply">Apply</button>  
    </Card>
</template>

<script>
import Card from "./Card.vue";
export default {
    name: "JobPosting",
    components: {
        Card
    },
    props: {
        job: Object
    },
    methods: {
        apply() {
            console.log("Applying to", this.job.title);
        }
    }
}
</script>

<style scoped>
.job-card {
    background: #f5f5f5;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}
</style>