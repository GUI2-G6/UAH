<template>
  <div id="uah-app">
    <header>
      <h1><router-link to="/" class="logo-link">UAH</router-link></h1>
      <p class="subtitle">Unified Application Hub</p>
      <nav class="nav">
        <router-link to="/" class="nav-link">Home</router-link>
        <router-link to="/status" class="nav-link">Status</router-link>
      </nav>
    </header>

    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App',
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f1117;
  color: #e1e4e8;
}

#uah-app {
  max-width: 900px;
  margin: 40px auto;
  padding: 0 20px;
}

header {
  text-align: center;
  margin-bottom: 40px;
}

h1 {
  font-size: 2.4rem;
  letter-spacing: 4px;
  color: #58a6ff;
}

.logo-link {
  color: inherit;
  text-decoration: none;
}

.subtitle {
  margin-top: 6px;
  color: #8b949e;
  font-size: 0.95rem;
}

.nav {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  gap: 24px;
}

.nav-link {
  color: #8b949e;
  text-decoration: none;
  font-size: 0.9rem;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.nav-link:hover {
  color: #e1e4e8;
}

.nav-link.router-link-active {
  color: #58a6ff;
  border-bottom-color: #58a6ff;
}

.status-card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 8px;
  padding: 24px;
}

.status-card h2 {
  font-size: 1rem;
  color: #8b949e;
  margin-bottom: 12px;
}

.status {
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.dot.green { background: #3fb950; }
.dot.red   { background: #f85149; }

.loading { color: #d29922; }
.error   { color: #f85149; }
.ok      { color: #3fb950; }
</style>

