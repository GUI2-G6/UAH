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
</template>


<script>
import JobPosting from "../components/JobPosting.vue";

export default {
  name: "JobBoard",
  components: { JobPosting },

  data() {
    return {
      jobs: []
    };
  },

  mounted() {
    this.jobs = [
      { id: 1, title: "Software Engineer", company: "Google", location: "Remote" },
      { id: 2, title: "Frontend Dev", company: "Amazon", location: "NYC" },
      { id: 3, title: "Backend Dev", company: "Meta", location: "SF" }
    ];
  }
}
</script>

<style src="./css/Job-board.css"></style>