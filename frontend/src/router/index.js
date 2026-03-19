import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Notifications from '../views/Notifications.vue'

const routes = [
  { path: '/', name: 'home', component: Home },
  { path: '/notifications', name: 'notifications', component: Notifications},
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
