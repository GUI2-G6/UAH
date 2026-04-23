import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { applyThemeFromStorage, initThemeListeners } from '@shared/js/themePreference.js'
import './assets/styles/base.css'
import './assets/styles/nav.css'
import './assets/styles/sections.css'

applyThemeFromStorage()
initThemeListeners()

createApp(App).use(router).mount('#app')
