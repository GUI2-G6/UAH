const browserApi = globalThis.browser
const chromeApi = globalThis.chrome

function runtimeErrorMessage() {
  return chromeApi?.runtime?.lastError?.message || ''
}

function callCallbackApi(target, methodName, ...args) {
  return new Promise((resolve, reject) => {
    const method = target?.[methodName]
    if (typeof method !== 'function') {
      reject(new Error(`Extension API method '${methodName}' is unavailable.`))
      return
    }

    try {
      method.call(target, ...args, (result) => {
        const message = runtimeErrorMessage()
        if (message) {
          reject(new Error(message))
          return
        }
        resolve(result)
      })
    } catch (error) {
      reject(error)
    }
  })
}

function wrapPromiseApi(target, methodName, ...args) {
  const method = target?.[methodName]
  if (typeof method !== 'function') {
    return Promise.reject(new Error(`Extension API method '${methodName}' is unavailable.`))
  }
  return Promise.resolve(method.call(target, ...args))
}

function extensionCall(targetFactory, methodName, ...args) {
  if (browserApi) {
    return wrapPromiseApi(targetFactory(browserApi), methodName, ...args)
  }
  if (chromeApi) {
    return callCallbackApi(targetFactory(chromeApi), methodName, ...args)
  }
  return Promise.reject(new Error('Browser extension APIs are unavailable in this context.'))
}

export function sendRuntimeMessage(message) {
  return extensionCall((api) => api.runtime, 'sendMessage', message)
}

export function addRuntimeMessageListener(handler) {
  const runtime = browserApi?.runtime || chromeApi?.runtime
  if (!runtime?.onMessage?.addListener) {
    throw new Error('runtime.onMessage is unavailable.')
  }

  runtime.onMessage.addListener((message, sender, sendResponse) => {
    Promise.resolve(handler(message, sender))
      .then((response) => sendResponse(response))
      .catch((error) => sendResponse({ ok: false, code: 'UNHANDLED_ERROR', message: String(error?.message || error) }))
    return true
  })
}

export function storageGet(areaName, keys) {
  return extensionCall((api) => api.storage[areaName], 'get', keys)
}

export function storageSet(areaName, value) {
  return extensionCall((api) => api.storage[areaName], 'set', value)
}

export function storageRemove(areaName, keys) {
  return extensionCall((api) => api.storage[areaName], 'remove', keys)
}

export function cookiesGet(details) {
  return extensionCall((api) => api.cookies, 'get', details)
}

export function cookiesRemove(details) {
  return extensionCall((api) => api.cookies, 'remove', details)
}

export function tabsCreate(details) {
  return extensionCall((api) => api.tabs, 'create', details)
}

export function tabsQuery(queryInfo) {
  return extensionCall((api) => api.tabs, 'query', queryInfo)
}

export function tabsGet(tabId) {
  return extensionCall((api) => api.tabs, 'get', tabId)
}

export function tabsRemove(tabId) {
  return extensionCall((api) => api.tabs, 'remove', tabId)
}

export function scriptingExecuteScript(injection) {
  return extensionCall((api) => api.scripting, 'executeScript', injection)
}

export function addTabsUpdatedListener(listener) {
  const tabs = browserApi?.tabs || chromeApi?.tabs
  if (!tabs?.onUpdated?.addListener) {
    throw new Error('tabs.onUpdated is unavailable.')
  }
  tabs.onUpdated.addListener(listener)
}

export function addTabsActivatedListener(listener) {
  const tabs = browserApi?.tabs || chromeApi?.tabs
  if (!tabs?.onActivated?.addListener) {
    throw new Error('tabs.onActivated is unavailable.')
  }
  tabs.onActivated.addListener(listener)
}

export function removeTabsUpdatedListener(listener) {
  const tabs = browserApi?.tabs || chromeApi?.tabs
  tabs?.onUpdated?.removeListener?.(listener)
}

export function addTabsRemovedListener(listener) {
  const tabs = browserApi?.tabs || chromeApi?.tabs
  if (!tabs?.onRemoved?.addListener) {
    throw new Error('tabs.onRemoved is unavailable.')
  }
  tabs.onRemoved.addListener(listener)
}

export function removeTabsRemovedListener(listener) {
  const tabs = browserApi?.tabs || chromeApi?.tabs
  tabs?.onRemoved?.removeListener?.(listener)
}
