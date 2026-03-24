<template>
    <div class="page">
        <div class="greeting">
            <h1>Job Board</h1>
            <p>Browse and apply to jobs in one click!</p>
        </div>
        <div class="dashboard">
            <JobPosting 
                v-for="job in jobs" 
                :key="job.id" 
                :job="job"
            />
        </div>
    </div>
    <!--Add pages for loading 20 jobs at a time-->
</template>


<script>
import JobPosting from "../components/JobPosting.vue";

export default {
  name: "JobBoard",
  components: { JobPosting },
  methods: {
    async loadJobs() {
      try {
        const res = await fetch('/api/jobs/search?page=1')
        const data = await res.json()
        console.log("RAW JOBS:", data)
        this.jobs = data
      } catch(e) {
        console.error("Failed to load jobs", e)
      }
    }
  },
  data() {
    return {
      jobs: []
    };
  },
  async mounted() {
    await this.loadJobs()
  }
}
</script>

<style scoped src="./css/Job-board.css"></style>