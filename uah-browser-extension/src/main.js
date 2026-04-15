import { createApp } from 'vue'

import App from './App.vue'
import './styles/popup.css'

const params = new URLSearchParams(window.location.search)
const surface = params.get('surface') === 'pinned' ? 'pinned' : 'popup'

document.documentElement.dataset.uahSurface = surface

createApp(App, { surface }).mount('#app')
