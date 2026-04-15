export const PINNED_UI_STATE_KEY = 'uah.extension.ui.state'

export const FLOATING_PANEL_MARGIN = 16
export const PINNED_PANEL_WIDTH = 196
export const PINNED_PANEL_HEIGHT = 380
export const PINNED_PANEL_MIN_WIDTH = 196
export const PINNED_PANEL_MIN_HEIGHT = 320
export const PINNED_PANEL_MAX_WIDTH = 720
export const DEBUG_PANEL_WIDTH = 340

export const DEFAULT_PINNED_UI_STATE = Object.freeze({
  pinEnabled: false,
  panelPosition: null,
  panelSize: null,
  panelResizeUnlocked: false,
  debugPosition: null,
})

function toFiniteNumber(value) {
  const normalized = Number(value)
  return Number.isFinite(normalized) ? normalized : null
}

export function normalizeFloatingPosition(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null

  const top = toFiniteNumber(value.top)
  const left = toFiniteNumber(value.left)

  if (top === null || left === null) return null
  return {
    top: Math.round(top),
    left: Math.round(left),
  }
}

export function normalizePanelSize(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null

  const width = toFiniteNumber(value.width)
  const height = toFiniteNumber(value.height)

  if (width === null || height === null) return null
  return {
    width: Math.round(width),
    height: Math.round(height),
  }
}

export function mergePinnedUiState(currentState = DEFAULT_PINNED_UI_STATE, patch = {}) {
  const normalizedCurrent = {
    pinEnabled: Boolean(currentState?.pinEnabled),
    panelPosition: normalizeFloatingPosition(currentState?.panelPosition),
    panelSize: normalizePanelSize(currentState?.panelSize),
    panelResizeUnlocked: Boolean(currentState?.panelResizeUnlocked),
    debugPosition: normalizeFloatingPosition(currentState?.debugPosition),
  }

  return {
    pinEnabled: typeof patch?.pinEnabled === 'boolean' ? patch.pinEnabled : normalizedCurrent.pinEnabled,
    panelPosition: Object.prototype.hasOwnProperty.call(patch || {}, 'panelPosition')
      ? normalizeFloatingPosition(patch?.panelPosition)
      : normalizedCurrent.panelPosition,
    panelSize: Object.prototype.hasOwnProperty.call(patch || {}, 'panelSize')
      ? normalizePanelSize(patch?.panelSize)
      : normalizedCurrent.panelSize,
    panelResizeUnlocked: typeof patch?.panelResizeUnlocked === 'boolean'
      ? patch.panelResizeUnlocked
      : normalizedCurrent.panelResizeUnlocked,
    debugPosition: Object.prototype.hasOwnProperty.call(patch || {}, 'debugPosition')
      ? normalizeFloatingPosition(patch?.debugPosition)
      : normalizedCurrent.debugPosition,
  }
}

export function buildDefaultFloatingPosition({
  viewportWidth = 1280,
  width = PINNED_PANEL_WIDTH,
  top = FLOATING_PANEL_MARGIN,
  margin = FLOATING_PANEL_MARGIN,
} = {}) {
  const nextLeft = Math.max(margin, Math.round(viewportWidth - width - margin))
  return {
    top: Math.max(margin, Math.round(top)),
    left: nextLeft,
  }
}

export function clampPanelSize(
  size,
  {
    viewportWidth = 1280,
    viewportHeight = 720,
    minWidth = PINNED_PANEL_MIN_WIDTH,
    minHeight = PINNED_PANEL_MIN_HEIGHT,
    maxWidth = PINNED_PANEL_MAX_WIDTH,
    margin = FLOATING_PANEL_MARGIN,
  } = {},
) {
  const normalized = normalizePanelSize(size) || {
    width: PINNED_PANEL_WIDTH,
    height: PINNED_PANEL_HEIGHT,
  }

  const allowedMaxWidth = Math.max(minWidth, Math.min(maxWidth, Math.round(viewportWidth - margin * 2)))
  const allowedMaxHeight = Math.max(minHeight, Math.round(viewportHeight - margin * 2))

  return {
    width: Math.min(allowedMaxWidth, Math.max(minWidth, normalized.width)),
    height: Math.min(allowedMaxHeight, Math.max(minHeight, normalized.height)),
  }
}

export function buildLockedPanelSize(viewport = {}) {
  return clampPanelSize(
    {
      width: PINNED_PANEL_WIDTH,
      height: PINNED_PANEL_HEIGHT,
    },
    viewport,
  )
}

export function clampFloatingPosition(
  position,
  {
    viewportWidth = 1280,
    viewportHeight = 720,
    width = PINNED_PANEL_WIDTH,
    height = PINNED_PANEL_HEIGHT,
    margin = FLOATING_PANEL_MARGIN,
  } = {},
) {
  const normalized = normalizeFloatingPosition(position)
    || buildDefaultFloatingPosition({ viewportWidth, width, margin })

  const maxLeft = Math.max(margin, Math.round(viewportWidth - width - margin))
  const maxTop = Math.max(margin, Math.round(viewportHeight - height - margin))

  return {
    left: Math.min(maxLeft, Math.max(margin, normalized.left)),
    top: Math.min(maxTop, Math.max(margin, normalized.top)),
  }
}
