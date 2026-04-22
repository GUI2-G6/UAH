import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/styles/base.css'
import './assets/styles/nav.css'
import './assets/styles/sections.css'

createApp(App).use(router).mount('#app')
