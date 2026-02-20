import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import StatusPage from '../views/StatusPage.vue'

const routes = [
  { path: '/', name: 'home', component: HomePage },
  { path: '/status', name: 'status', component: StatusPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
