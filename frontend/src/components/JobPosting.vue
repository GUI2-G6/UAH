<template>
    <div class="card job-card">
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