<template>
  <section class="landing-redirect" aria-live="polite">
    <h1>Redirecting to the UAH landing page...</h1>
    <p>
      If redirect does not start,
      <a :href="landingUrl">open the landing page</a>
      or
      <router-link to="/login">sign in directly</router-link>.
    </p>
  </section>
</template>

<script>
const DEFAULT_LANDING_URL = 'https://uahapp.com'

export default {
  name: 'Landing',
  data() {
    return {
      landingUrl: DEFAULT_LANDING_URL,
    }
  },
  mounted() {
    const configured = String(import.meta.env.VITE_PUBLIC_LANDING_URL || '').trim()
    this.landingUrl = configured || DEFAULT_LANDING_URL
    window.location.replace(this.landingUrl)
  },
}
</script>

<style scoped>
.landing-redirect {
  min-height: 60vh;
  display: grid;
  place-content: center;
  gap: 0.8rem;
  padding: 2rem;
  text-align: center;
}

.landing-redirect a {
  font-weight: 700;
}
</style>
