import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { draggableModalDirective } from './lib/draggableModalDirective'
import { installDebugFetchTracker } from './lib/debugDiagnostics'
import { assertSafeLocalModeConfig, initializeLocalMockApi } from './lib/localMockApi'

// Polyfill for environments where `crypto.randomUUID` is unavailable.
// Some browsers only expose it in secure contexts (https/localhost).
(() => {
	const cryptoObj = globalThis.crypto
	if (!cryptoObj || typeof cryptoObj.randomUUID === 'function') return

	const toHex = (bytes) => Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')

	cryptoObj.randomUUID = () => {
		let bytes
		if (typeof cryptoObj.getRandomValues === 'function') {
			bytes = cryptoObj.getRandomValues(new Uint8Array(16))
		} else {
			bytes = new Uint8Array(16)
			for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256)
		}

		// RFC 4122 version 4
		bytes[6] = (bytes[6] & 0x0f) | 0x40
		bytes[8] = (bytes[8] & 0x3f) | 0x80

		const hex = toHex(bytes)
		return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
	}
})()

try {
	assertSafeLocalModeConfig()
} catch (error) {
	console.error(error)
	const target = document.getElementById('app')
	if (target) {
		target.textContent = String(error?.message || error)
	}
	throw error
}

initializeLocalMockApi()
installDebugFetchTracker()

const app = createApp(App)
app.directive('draggable-modal', draggableModalDirective)
app.use(router).mount('#app')

