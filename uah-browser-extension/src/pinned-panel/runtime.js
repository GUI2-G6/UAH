import { requestBackground } from '../lib/messages.js'
import { enableFloatingDrag } from '../lib/floatingDrag.js'
import {
  buildLockedPanelSize,
  buildDefaultFloatingPosition,
  clampPanelSize,
  clampFloatingPosition,
  DEFAULT_PINNED_UI_STATE,
  PINNED_PANEL_HEIGHT,
  PINNED_PANEL_MAX_WIDTH,
  PINNED_PANEL_MIN_HEIGHT,
  PINNED_PANEL_MIN_WIDTH,
  PINNED_PANEL_WIDTH,
} from '../lib/pinnedUiState.js'

const PANEL_ID = 'uah-pinned-panel-root'
const STYLE_ID = 'uah-pinned-panel-style'

function ensureStyles(doc = document) {
  if (doc.getElementById(STYLE_ID)) return

  const style = doc.createElement('style')
  style.id = STYLE_ID
  style.textContent = `
    #${PANEL_ID} {
      position: fixed;
      z-index: 2147483645;
      width: ${PINNED_PANEL_WIDTH}px;
      height: min(${PINNED_PANEL_HEIGHT}px, calc(100vh - 32px));
      min-width: ${PINNED_PANEL_MIN_WIDTH}px;
      min-height: ${PINNED_PANEL_MIN_HEIGHT}px;
      max-width: min(${PINNED_PANEL_MAX_WIDTH}px, calc(100vw - 32px));
      max-height: calc(100vh - 32px);
      border-radius: 18px;
      border: 1px solid rgba(191, 219, 254, 0.92);
      box-shadow: 0 24px 64px rgba(15, 23, 42, 0.28);
      overflow: hidden;
      background: rgba(248, 250, 252, 0.96);
      backdrop-filter: blur(16px);
      resize: none;
    }
    #${PANEL_ID}::after {
      content: "";
      position: absolute;
      right: 0;
      bottom: 0;
      width: 18px;
      height: 18px;
      background: rgba(248, 250, 252, 0.98);
      pointer-events: none;
    }
    #${PANEL_ID}.uah-pinned-panel--resize-unlocked {
      resize: both;
    }
    #${PANEL_ID}.uah-pinned-panel--resize-unlocked::after {
      display: none;
    }
    #${PANEL_ID} .uah-pinned-panel__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 14px;
      background: linear-gradient(135deg, rgba(239, 246, 255, 0.98), rgba(255, 255, 255, 0.96));
      border-bottom: 1px solid rgba(226, 232, 240, 0.9);
      cursor: move;
      user-select: none;
    }
    #${PANEL_ID} .uah-pinned-panel__eyebrow {
      margin: 0 0 4px;
      color: #1d4ed8;
      font: 700 11px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    #${PANEL_ID} .uah-pinned-panel__title {
      margin: 0;
      color: #0f172a;
      font: 700 15px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    #${PANEL_ID} .uah-pinned-panel__actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }
    #${PANEL_ID} .uah-pinned-panel__button {
      border: 1px solid rgba(191, 219, 254, 1);
      border-radius: 999px;
      background: white;
      color: #1d4ed8;
      padding: 7px 11px;
      font: 700 12px/1 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      cursor: pointer;
    }
    #${PANEL_ID} .uah-pinned-panel__button--active {
      background: #1d4ed8;
      border-color: #1d4ed8;
      color: white;
    }
    #${PANEL_ID} iframe {
      display: block;
      width: 100%;
      height: calc(100% - 60px);
      border: 0;
      background: transparent;
    }
    #${PANEL_ID}.uah-pinned-panel--compact {
      border-radius: 16px;
    }
    #${PANEL_ID}.uah-pinned-panel--compact .uah-pinned-panel__header {
      flex-wrap: wrap;
      align-items: flex-start;
    }
    #${PANEL_ID}.uah-pinned-panel--compact .uah-pinned-panel__actions {
      width: 100%;
      justify-content: flex-end;
    }
  `

  doc.head.appendChild(style)
}

function getPanel(doc = document) {
  return doc.getElementById(PANEL_ID)
}

function removePanel(doc = document) {
  getPanel(doc)?.remove()
}

function buildPopupUrl() {
  // The pinned surface reuses the same popup app in an iframe so background
  // messaging, auth state, and UI logic stay shared across both surfaces.
  const popupUrl = globalThis.chrome?.runtime?.getURL?.('popup.html') || ''
  return `${popupUrl}?surface=pinned`
}

export function registerPinnedPanelRuntime(win = window, doc = document) {
  if (win.__UAH_PINNED_PANEL__) return win.__UAH_PINNED_PANEL__

  const state = {
    uiState: { ...DEFAULT_PINNED_UI_STATE },
    drag: null,
    resizeHandler: null,
    panelResizeObserver: null,
  }

  function cleanupDrag() {
    state.drag?.destroy?.()
    state.drag = null
  }

  function resolvePanelSize() {
    const viewport = {
      viewportWidth: win.innerWidth,
      viewportHeight: win.innerHeight,
    }

    if (!state.uiState.panelResizeUnlocked) {
      return buildLockedPanelSize(viewport)
    }

    return clampPanelSize(state.uiState.panelSize, viewport)
  }

  function updateResizeMode(root) {
    const resizeUnlocked = Boolean(state.uiState.panelResizeUnlocked)
    root.classList.toggle('uah-pinned-panel--resize-unlocked', resizeUnlocked)
  }

  function updatePosition(root, position) {
    const panelSize = resolvePanelSize()

    root.style.width = `${panelSize.width}px`
    root.style.height = `${panelSize.height}px`
    root.classList.toggle('uah-pinned-panel--compact', panelSize.width < 340)
    updateResizeMode(root)

    const nextPosition = clampFloatingPosition(
      position || buildDefaultFloatingPosition({ viewportWidth: win.innerWidth, width: PINNED_PANEL_WIDTH }),
      {
        viewportWidth: win.innerWidth,
        viewportHeight: win.innerHeight,
        width: panelSize.width,
        height: panelSize.height,
      },
    )

    state.drag?.setPosition(nextPosition)
  }

  function attachDrag(root) {
    cleanupDrag()
    const handle = root.querySelector('.uah-pinned-panel__header')

    state.drag = enableFloatingDrag({
      handle,
      target: root,
      initialPosition: state.uiState.panelPosition,
      defaultPosition: buildDefaultFloatingPosition({ viewportWidth: win.innerWidth, width: PINNED_PANEL_WIDTH }),
      fallbackSize: { width: PINNED_PANEL_WIDTH, height: PINNED_PANEL_HEIGHT },
      onCommit(position) {
        state.uiState.panelPosition = position
        requestBackground('setPinnedUiState', { panelPosition: position }).catch(() => null)
      },
      win,
    })
  }

  function ensureResizeHandler(root) {
    if (state.resizeHandler) return

    state.resizeHandler = () => {
      state.uiState.panelSize = clampPanelSize(state.uiState.panelSize, {
        viewportWidth: win.innerWidth,
        viewportHeight: win.innerHeight,
      })
      const fallbackPosition = state.drag?.getPosition?.() || state.uiState.panelPosition
      updatePosition(root, fallbackPosition)
    }

    win.addEventListener('resize', state.resizeHandler)
  }

  function ensurePanelResizeObserver(root) {
    if (state.panelResizeObserver || typeof globalThis.ResizeObserver !== 'function') return

    state.panelResizeObserver = new ResizeObserver(() => {
      const nextSize = clampPanelSize(
        {
          width: root.offsetWidth,
          height: root.offsetHeight,
        },
        {
          viewportWidth: win.innerWidth,
          viewportHeight: win.innerHeight,
        },
      )

      root.style.width = `${nextSize.width}px`
      root.style.height = `${nextSize.height}px`
      root.classList.toggle('uah-pinned-panel--compact', nextSize.width < 340)

      if (
        state.uiState.panelSize?.width !== nextSize.width
        || state.uiState.panelSize?.height !== nextSize.height
      ) {
        state.uiState.panelSize = nextSize
        const fallbackPosition = state.drag?.getPosition?.() || state.uiState.panelPosition
        updatePosition(root, fallbackPosition)
        requestBackground('setPinnedUiState', { panelSize: nextSize }).catch(() => null)
      }
    })

    state.panelResizeObserver.observe(root)
  }

  function ensurePanel() {
    let root = getPanel(doc)
    if (root) return root

    const initialPanelSize = resolvePanelSize()
    const initialPanelPosition = clampFloatingPosition(
      state.uiState.panelPosition || buildDefaultFloatingPosition({ viewportWidth: win.innerWidth, width: initialPanelSize.width }),
      {
        viewportWidth: win.innerWidth,
        viewportHeight: win.innerHeight,
        width: initialPanelSize.width,
        height: initialPanelSize.height,
      },
    )

    root = doc.createElement('div')
    root.id = PANEL_ID
    root.style.width = `${initialPanelSize.width}px`
    root.style.height = `${initialPanelSize.height}px`
    root.style.left = `${initialPanelPosition.left}px`
    root.style.top = `${initialPanelPosition.top}px`
    root.style.display = 'none'
    root.classList.toggle('uah-pinned-panel--compact', initialPanelSize.width < 340)
    root.innerHTML = `
      <div class="uah-pinned-panel__header">
        <div>
          <p class="uah-pinned-panel__eyebrow">UAH Browser Companion</p>
          <p class="uah-pinned-panel__title">Pinned applicant panel</p>
        </div>
        <div class="uah-pinned-panel__actions">
          <button class="uah-pinned-panel__button uah-pinned-panel__button--resize" type="button">Unlock size</button>
          <button class="uah-pinned-panel__button uah-pinned-panel__button--active uah-pinned-panel__button--pin" type="button">Unpin</button>
          <button class="uah-pinned-panel__button uah-pinned-panel__button--close" type="button" aria-label="Close">X</button>
        </div>
      </div>
      <iframe title="UAH pinned panel" src="${buildPopupUrl()}"></iframe>
    `

    const resizeButton = root.querySelector('.uah-pinned-panel__button--resize')
    const syncResizeButton = () => {
      const unlocked = Boolean(state.uiState.panelResizeUnlocked)
      resizeButton?.classList.toggle('uah-pinned-panel__button--active', unlocked)
      if (resizeButton) {
        resizeButton.textContent = unlocked ? 'Lock size' : 'Unlock size'
      }
    }

    resizeButton?.addEventListener('click', async () => {
      const nextUnlocked = !state.uiState.panelResizeUnlocked
      state.uiState.panelResizeUnlocked = nextUnlocked
      if (nextUnlocked) {
        state.uiState.panelSize = clampPanelSize(
          {
            width: root.offsetWidth || PINNED_PANEL_WIDTH,
            height: root.offsetHeight || PINNED_PANEL_HEIGHT,
          },
          {
            viewportWidth: win.innerWidth,
            viewportHeight: win.innerHeight,
          },
        )
      }
      if (!nextUnlocked) {
        state.uiState.panelSize = buildLockedPanelSize({
          viewportWidth: win.innerWidth,
          viewportHeight: win.innerHeight,
        })
      }
      updateResizeMode(root)
      syncResizeButton()
      updatePosition(root, state.drag?.getPosition?.() || state.uiState.panelPosition)
      await requestBackground('setPinnedUiState', { panelResizeUnlocked: nextUnlocked }).catch(() => null)
    })

    root.querySelector('.uah-pinned-panel__button--pin')?.addEventListener('click', async () => {
      await requestBackground('setPinnedUiState', { pinEnabled: false }).catch(() => null)
      api.hide()
    })

    root.querySelector('.uah-pinned-panel__button--close')?.addEventListener('click', async () => {
      await requestBackground('dismissPinnedPanel').catch(() => null)
      api.hide()
    })

    doc.body.appendChild(root)
    syncResizeButton()
    attachDrag(root)
    ensureResizeHandler(root)
    ensurePanelResizeObserver(root)
    updatePosition(root, initialPanelPosition)
    return root
  }

  const api = {
    show(nextUiState = {}) {
      ensureStyles(doc)
      state.uiState = { ...state.uiState, ...nextUiState }
      const root = ensurePanel()
      updatePosition(root, state.uiState.panelPosition)
      root.style.display = 'block'
      return { ok: true }
    },
    hide() {
      cleanupDrag()
      removePanel(doc)
      state.panelResizeObserver?.disconnect?.()
      state.panelResizeObserver = null
      if (state.resizeHandler) {
        win.removeEventListener('resize', state.resizeHandler)
        state.resizeHandler = null
      }
      return { ok: true }
    },
  }

  win.__UAH_PINNED_PANEL__ = api
  return api
}
