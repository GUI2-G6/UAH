<template>
    <div class="job-card">
        <h3>{{ job.title }}</h3>
        <p>{{ job.company }}</p>
        <p>{{ job.location }}</p>
        <button @click="apply">Apply</button>
    </div>
</template>

<script>
export default {
    name: "JobPosting",
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