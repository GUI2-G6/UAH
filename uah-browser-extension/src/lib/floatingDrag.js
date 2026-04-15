import { buildDefaultFloatingPosition, clampFloatingPosition } from './pinnedUiState.js'

function applyTargetPosition(target, position) {
  if (!target || !position) return
  target.style.left = `${position.left}px`
  target.style.top = `${position.top}px`
}

function readViewportBounds(target, win, fallbackSize = {}) {
  return {
    viewportWidth: win.innerWidth || 1280,
    viewportHeight: win.innerHeight || 720,
    width: target?.offsetWidth || fallbackSize.width || 0,
    height: target?.offsetHeight || fallbackSize.height || 0,
  }
}

export function enableFloatingDrag({
  handle,
  target,
  initialPosition = null,
  defaultPosition = null,
  ignoreSelector = 'button, a, input, select, textarea, [role="button"]',
  fallbackSize = {},
  onMove = null,
  onCommit = null,
  win = window,
} = {}) {
  if (!handle || !target || !win?.addEventListener) {
    return {
      getPosition: () => null,
      setPosition() {},
      destroy() {},
    }
  }

  let dragPosition = clampFloatingPosition(
    initialPosition || defaultPosition || buildDefaultFloatingPosition(readViewportBounds(target, win, fallbackSize)),
    readViewportBounds(target, win, fallbackSize),
  )
  let dragging = false
  let startPointerX = 0
  let startPointerY = 0
  let startLeft = dragPosition.left
  let startTop = dragPosition.top

  function setPosition(nextPosition, emitMove = true) {
    dragPosition = clampFloatingPosition(nextPosition, readViewportBounds(target, win, fallbackSize))
    applyTargetPosition(target, dragPosition)
    if (emitMove && typeof onMove === 'function') onMove({ ...dragPosition })
  }

  function onPointerMove(event) {
    if (!dragging) return
    event.preventDefault()
    setPosition({
      left: startLeft + (event.clientX - startPointerX),
      top: startTop + (event.clientY - startPointerY),
    })
  }

  function onPointerUp() {
    if (!dragging) return
    dragging = false
    win.removeEventListener('pointermove', onPointerMove)
    win.removeEventListener('pointerup', onPointerUp)
    if (typeof onCommit === 'function') onCommit({ ...dragPosition })
  }

  function onPointerDown(event) {
    if (event.button !== undefined && event.button !== 0) return
    if (ignoreSelector && event.target?.closest?.(ignoreSelector)) return

    dragging = true
    startPointerX = event.clientX
    startPointerY = event.clientY
    startLeft = dragPosition.left
    startTop = dragPosition.top

    win.addEventListener('pointermove', onPointerMove)
    win.addEventListener('pointerup', onPointerUp)
  }

  handle.addEventListener('pointerdown', onPointerDown)
  setPosition(dragPosition, false)

  return {
    getPosition() {
      return { ...dragPosition }
    },
    setPosition(nextPosition) {
      setPosition(nextPosition, false)
    },
    destroy() {
      dragging = false
      handle.removeEventListener('pointerdown', onPointerDown)
      win.removeEventListener('pointermove', onPointerMove)
      win.removeEventListener('pointerup', onPointerUp)
    },
  }
}
