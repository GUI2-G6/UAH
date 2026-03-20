import { createRouter, createWebHistory } from 'vue-router'

const modules = import.meta.glob('../views/*.vue')

/* This grabs everything from and generates routes for everything in the views folder */
const routes = Object.keys(modules).map((path) => {
  const name = path
    .split('/')
    .pop()
    .replace('.vue', '')

  return {
    path: name.toLowerCase() === 'home' ? '/' : `/${name.toLowerCase()}`,
    name: name.toLowerCase(),
    component: modules[path]
  }
})


const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
