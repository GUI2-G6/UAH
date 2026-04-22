<template>
  <section class="landing-gateway">
    <div class="landing-card">
      <p class="eyebrow">Unified Application Hub</p>
      <h1>Your AI job-search workspace starts here.</h1>
      <p class="subtitle">
        Explore UAH first, then sign in when you are ready to continue into your workspace.
      </p>
      <div class="actions">
        <router-link class="button primary" to="/login">Sign in</router-link>
        <router-link class="button secondary" to="/register">Create account</router-link>
      </div>
      <p class="meta">
        Need full product details first?
        <a :href="marketingUrl" target="_blank" rel="noopener noreferrer">Visit the public landing page</a>.
      </p>
    </div>
  </section>
</template>

<script>
const DEFAULT_MARKETING_URL = 'https://uahapp.com'

export default {
  name: 'Landing',
  data() {
    return {
      marketingUrl: DEFAULT_MARKETING_URL,
    }
  },
  created() {
    const configured = String(import.meta.env.VITE_PUBLIC_LANDING_URL || '').trim()
    this.marketingUrl = configured || DEFAULT_MARKETING_URL
  },
}
</script>

<style scoped>
.landing-gateway {
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.landing-card {
  width: min(720px, 100%);
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  box-shadow: 0 24px 40px rgba(15, 23, 42, 0.08);
  padding: 2.5rem;
  text-align: center;
}

.eyebrow {
  margin: 0 0 0.8rem;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f6f8f;
}

h1 {
  margin: 0;
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  line-height: 1.15;
  color: #0f172a;
}

.subtitle {
  margin: 1rem auto 0;
  max-width: 52ch;
  color: #334155;
  line-height: 1.6;
}

.actions {
  margin-top: 1.8rem;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.8rem;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 150px;
  padding: 0.72rem 1.1rem;
  border-radius: 999px;
  font-weight: 700;
  text-decoration: none;
}

.button.primary {
  background: #0f172a;
  color: #f8fafc;
}

.button.secondary {
  border: 1px solid #0f172a;
  color: #0f172a;
}

.meta {
  margin-top: 1.2rem;
  color: #475569;
}

.meta a {
  color: #0f6f8f;
  font-weight: 700;
}

@media (max-width: 640px) {
  .landing-card {
    padding: 1.5rem;
    border-radius: 16px;
  }

  .button {
    width: 100%;
  }
}
</style>
