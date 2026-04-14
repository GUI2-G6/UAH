import { sendRuntimeMessage } from './extensionApi'

export async function requestBackground(type, payload = {}) {
  const response = await sendRuntimeMessage({ type, payload })
  if (!response?.ok) {
    const error = new Error(response?.message || 'Extension request failed.')
    error.code = response?.code || 'EXTENSION_REQUEST_FAILED'
    error.status = response?.status || null
    throw error
  }
  return response.data
}
