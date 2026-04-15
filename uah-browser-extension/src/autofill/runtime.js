import { buildDomPlan, clearHighlights, applyHighlights, computePlanStats, fillPlan } from './dom.js'
import { requestBackground } from '../lib/messages.js'
import { enableFloatingDrag } from '../lib/floatingDrag.js'
import {
  buildDefaultFloatingPosition,
  clampFloatingPosition,
  DEBUG_PANEL_WIDTH,
  DEFAULT_PINNED_UI_STATE,
} from '../lib/pinnedUiState.js'

const OVERLAY_ID = 'uah-profile-autofill-overlay'
const STYLE_ID = 'uah-profile-autofill-style'

function escapeHtml(value) {
  const span = document.createElement('span')
  span.textContent = String(value ?? '')
  return span.innerHTML
}

function ensureStyles(doc = document) {
  if (doc.getElementById(STYLE_ID)) return

  const style = doc.createElement('style')
  style.id = STYLE_ID
  style.textContent = `
    #${OVERLAY_ID} {
      position: fixed;
      width: ${DEBUG_PANEL_WIDTH}px;
      max-height: 82vh;
      overflow: auto;
      z-index: 2147483646;
      font: 13px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #0f172a;
      background: rgba(255, 255, 255, 0.98);
      border: 1px solid rgba(148, 163, 184, 0.45);
      border-radius: 14px;
      box-shadow: 0 18px 48px rgba(15, 23, 42, 0.18);
    }
    #${OVERLAY_ID} .uah-autofill-header,
    #${OVERLAY_ID} .uah-autofill-body {
      padding: 12px 14px;
    }
    #${OVERLAY_ID} .uah-autofill-header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      border-bottom: 1px solid rgba(226, 232, 240, 0.9);
      background: linear-gradient(135deg, #eff6ff, #f8fafc);
      cursor: move;
      user-select: none;
    }
    #${OVERLAY_ID} .uah-autofill-kicker {
      margin: 0 0 4px;
      color: #1d4ed8;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    #${OVERLAY_ID} .uah-autofill-title,
    #${OVERLAY_ID} .uah-autofill-note,
    #${OVERLAY_ID} .uah-autofill-path,
    #${OVERLAY_ID} .uah-autofill-preview {
      margin: 0;
    }
    #${OVERLAY_ID} .uah-autofill-title {
      font-size: 14px;
      font-weight: 700;
    }
    #${OVERLAY_ID} .uah-autofill-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    #${OVERLAY_ID} .uah-autofill-btn,
    #${OVERLAY_ID} .uah-autofill-close {
      border: 1px solid rgba(191, 219, 254, 1);
      border-radius: 999px;
      background: white;
      color: #1d4ed8;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }
    #${OVERLAY_ID} .uah-autofill-pills {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }
    #${OVERLAY_ID} .uah-autofill-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      border-radius: 999px;
      background: #eff6ff;
      color: #1d4ed8;
      font-size: 12px;
      font-weight: 700;
    }
    #${OVERLAY_ID} .uah-autofill-note {
      color: #475569;
      margin-bottom: 10px;
    }
    #${OVERLAY_ID} .uah-autofill-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    #${OVERLAY_ID} .uah-autofill-item {
      padding: 10px;
      border: 1px solid rgba(226, 232, 240, 0.95);
      border-radius: 10px;
      background: #f8fafc;
      cursor: pointer;
    }
    #${OVERLAY_ID} .uah-autofill-item:hover {
      border-color: rgba(96, 165, 250, 0.9);
      background: #eff6ff;
    }
    #${OVERLAY_ID} .uah-autofill-item-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 4px;
    }
    #${OVERLAY_ID} .uah-autofill-item-title {
      font-weight: 700;
      color: #0f172a;
    }
    #${OVERLAY_ID} .uah-autofill-item-score {
      color: #475569;
      font-size: 11px;
      white-space: nowrap;
    }
    #${OVERLAY_ID} .uah-autofill-path {
      color: #334155;
      font-size: 11px;
      word-break: break-word;
    }
    #${OVERLAY_ID} .uah-autofill-preview {
      color: #475569;
      font-size: 11px;
      margin-top: 4px;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .uah-fill-good { outline: 2px solid #16a34a !important; }
    .uah-fill-review { outline: 2px solid #d97706 !important; }
    .uah-fill-missing { outline: 2px solid #dc2626 !important; }
  `

  doc.head.appendChild(style)
}

function getOverlay(doc = document) {
  return doc.getElementById(OVERLAY_ID)
}

function cloneTokenMap(tokenMap) {
  return tokenMap && typeof tokenMap === 'object' ? { ...tokenMap } : {}
}

export function registerAutofillRuntime(win = window, doc = document) {
  if (win.__UAH_RESUME_TESTER__) return win.__UAH_RESUME_TESTER__

  const state = {
    currentPlan: null,
    currentTokens: null,
    notice: '',
    uiState: { ...DEFAULT_PINNED_UI_STATE },
    overlayDrag: null,
  }

  function persistDebugPosition(position) {
    state.uiState.debugPosition = position
    requestBackground('setPinnedUiState', { debugPosition: position }).catch(() => null)
  }

  function teardownOverlay() {
    const existingOverlay = getOverlay(doc)
    if (state.overlayDrag) {
      state.uiState.debugPosition = state.overlayDrag.getPosition()
      state.overlayDrag.destroy()
      state.overlayDrag = null
    }
    existingOverlay?.remove()
  }

  function closeDebugOverlay() {
    teardownOverlay()
  }

  function renderOverlay() {
    teardownOverlay()
    if (!state.currentPlan) return

    const stats = computePlanStats(state.currentPlan)
    const root = doc.createElement('div')
    root.id = OVERLAY_ID

    const items = state.currentPlan
      .filter((item) => item.matchPath || item.required)
      .sort((left, right) => {
        const leftScore = left.matchPath ? left.matchScore : -1
        const rightScore = right.matchPath ? right.matchScore : -1
        return rightScore - leftScore
      })
      .slice(0, 30)

    root.innerHTML = `
      <div class="uah-autofill-header">
        <div>
          <p class="uah-autofill-kicker">UAH Autofill Debug</p>
          <p class="uah-autofill-title">Manual scan plan for this page</p>
        </div>
        <button class="uah-autofill-close" type="button" aria-label="Close">Close</button>
      </div>
      <div class="uah-autofill-body">
        <div class="uah-autofill-pills">
          <span class="uah-autofill-pill">Fields <b>${stats.total}</b></span>
          <span class="uah-autofill-pill">Good <b>${stats.good}</b></span>
          <span class="uah-autofill-pill">Review <b>${stats.review}</b></span>
          <span class="uah-autofill-pill">Missing <b>${stats.missing}</b></span>
        </div>
        <p class="uah-autofill-note">${escapeHtml(state.notice || 'Highlighting fields matched from the selected UAH profile.')}</p>
        <div class="uah-autofill-actions">
          <button class="uah-autofill-btn" type="button" data-action="fill">Fill matched fields</button>
          <button class="uah-autofill-btn" type="button" data-action="rescan">Re-scan page</button>
        </div>
        <div class="uah-autofill-list"></div>
      </div>
    `

    const list = root.querySelector('.uah-autofill-list')
    items.forEach((item) => {
      const badge = item.matchPath ? `${Math.round(item.matchScore * 100)}%` : 'Required'
      const title = item.label?.trim() || item.name || item.id || '(unlabeled field)'
      const preview = item.matchPath && state.currentTokens?.[item.matchPath] !== undefined
        ? String(state.currentTokens[item.matchPath]).slice(0, 80)
        : ''
      const row = doc.createElement('button')
      row.type = 'button'
      row.className = 'uah-autofill-item'
      row.innerHTML = `
        <div class="uah-autofill-item-top">
          <span class="uah-autofill-item-title">${escapeHtml(title)}</span>
          <span class="uah-autofill-item-score">${escapeHtml(badge)}</span>
        </div>
        <p class="uah-autofill-path">${escapeHtml(item.matchPath || 'No token match')}</p>
        ${preview ? `<p class="uah-autofill-preview">${escapeHtml(preview)}</p>` : ''}
      `
      row.addEventListener('click', () => {
        item.el?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
        item.el?.focus?.()
      })
      list.appendChild(row)
    })

    root.querySelector('.uah-autofill-close')?.addEventListener('click', closeDebugOverlay)
    root.querySelector('[data-action="fill"]')?.addEventListener('click', () => {
      win.__UAH_RESUME_TESTER__?.fill(state.currentTokens)
    })
    root.querySelector('[data-action="rescan"]')?.addEventListener('click', () => {
      state.currentPlan = buildDomPlan(state.currentTokens, doc)
      state.notice = 'Re-scanned the current page.'
      clearHighlights(doc)
      applyHighlights(state.currentPlan)
      renderOverlay()
    })

    doc.body.appendChild(root)

    state.overlayDrag = enableFloatingDrag({
      handle: root.querySelector('.uah-autofill-header'),
      target: root,
      initialPosition: state.uiState.debugPosition,
      defaultPosition: buildDefaultFloatingPosition({ viewportWidth: win.innerWidth, width: DEBUG_PANEL_WIDTH }),
      fallbackSize: {
        width: DEBUG_PANEL_WIDTH,
        height: root.offsetHeight || 420,
      },
      onCommit(position) {
        persistDebugPosition(position)
      },
      win,
    })

    state.overlayDrag.setPosition(
      clampFloatingPosition(
        state.uiState.debugPosition || buildDefaultFloatingPosition({ viewportWidth: win.innerWidth, width: DEBUG_PANEL_WIDTH }),
        {
          viewportWidth: win.innerWidth,
          viewportHeight: win.innerHeight,
          width: root.offsetWidth || DEBUG_PANEL_WIDTH,
          height: root.offsetHeight || 420,
        },
      ),
    )
  }

  function refreshOverlay() {
    clearHighlights(doc)
    if (state.currentPlan) applyHighlights(state.currentPlan)
    renderOverlay()
  }

  win.addEventListener('resize', () => {
    if (!state.overlayDrag) return
    state.overlayDrag.setPosition(state.overlayDrag.getPosition())
  })

  const api = {
    configure(nextUiState = {}) {
      state.uiState = { ...state.uiState, ...nextUiState }
      if (state.overlayDrag) {
        state.overlayDrag.setPosition(state.uiState.debugPosition || state.overlayDrag.getPosition())
      }
    },
    scan(tokenMap) {
      ensureStyles(doc)
      state.currentTokens = cloneTokenMap(tokenMap)
      state.currentPlan = buildDomPlan(state.currentTokens, doc)
      state.notice = 'Scanned visible inputs, textareas, and selects on the current page.'
      refreshOverlay()
      return computePlanStats(state.currentPlan)
    },
    fill(tokenMap) {
      ensureStyles(doc)
      const nextTokens = cloneTokenMap(tokenMap)
      if (Object.keys(nextTokens).length) {
        state.currentTokens = nextTokens
      }
      if (!state.currentPlan || !state.currentTokens) {
        state.currentTokens = state.currentTokens || nextTokens
        state.currentPlan = buildDomPlan(state.currentTokens, doc)
      }
      const filled = fillPlan(state.currentPlan, state.currentTokens)
      state.notice = `Filled ${filled} field${filled === 1 ? '' : 's'} from the active plan.`
      refreshOverlay()
      return { filled, total: state.currentPlan.length }
    },
    remove() {
      teardownOverlay()
      doc.getElementById(STYLE_ID)?.remove()
      clearHighlights(doc)
      state.currentPlan = null
      state.currentTokens = null
      state.notice = ''
      return { ok: true }
    },
    getStats() {
      if (!state.currentPlan) return null
      return computePlanStats(state.currentPlan)
    },
  }

  win.__UAH_RESUME_TESTER__ = api
  return api
}
