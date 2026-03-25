const LOCATION_CACHE_KEY = 'uah_location_cache_v1'
const LOCATION_CACHE_TTL_MS = 24 * 60 * 60 * 1000

export function getCachedLocation() {
    try {
        const raw = localStorage.getItem(LOCATION_CACHE_KEY)
        if (!raw) return null

        const payload = JSON.parse(raw)
        const savedAt = Number(payload.savedAt || 0)
        if (!savedAt || Date.now() - savedAt > LOCATION_CACHE_TTL_MS) {
            localStorage.removeItem(LOCATION_CACHE_KEY)
            return null
        }

        return payload
    } catch {
        return null
    }
}

export function setCachedLocation(location) {
    const payload = {
        ...location,
        savedAt: Date.now(),
    }
    localStorage.setItem(LOCATION_CACHE_KEY, JSON.stringify(payload))
}

export function clearCachedLocation() {
    localStorage.removeItem(LOCATION_CACHE_KEY)
}

export function requestBrowserLocation(options = {}) {
    const geolocation = navigator.geolocation
    if (!geolocation) {
        return Promise.reject(new Error('Geolocation is not supported by this browser'))
    }

    return new Promise((resolve, reject) => {
        geolocation.getCurrentPosition(
            (position) => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    source: 'browser',
                })
            },
            (error) => {
                reject(error)
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0,
                ...options,
            }
        )
    })
}
