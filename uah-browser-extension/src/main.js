import { createApp } from 'vue'

import App from './App.vue'
import { requestBackground } from './lib/messages'
import { applyDocumentTheme, normalizeThemePreference, resolveEffectiveTheme } from './lib/themeMode'
import './styles/popup.css'

const params = new URLSearchParams(window.location.search)
const surface = params.get('surface') === 'pinned' ? 'pinned' : 'popup'

document.documentElement.dataset.uahSurface = surface

let initialThemePreference = 'system'

try {
  const uiState = await requestBackground('getPinnedUiState')
  initialThemePreference = normalizeThemePreference(uiState?.themePreference)
} catch {
  initialThemePreference = 'system'
}

applyDocumentTheme(resolveEffectiveTheme(initialThemePreference))

createApp(App, { surface, initialThemePreference }).mount('#app')
