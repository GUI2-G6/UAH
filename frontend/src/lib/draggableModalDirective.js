let zCounter = 1500

function clamp(value, min, max) {
  if (value < min) return min
  if (value > max) return max
  return value
}

export const draggableModalDirective = {
  mounted(el, binding) {
    const options = binding?.value || {}
    const handleSelector = options.handle || ".drag-handle"
    const handle = el.querySelector(handleSelector)
    if (!handle) return

    handle.style.cursor = "grab"

    const state = {
      dragging: false,
      startPointerX: 0,
      startPointerY: 0,
      startLeft: 0,
      startTop: 0,
    }

    const ensurePositioning = () => {
      const rect = el.getBoundingClientRect()
      el.style.position = "fixed"
      el.style.margin = "0"
      el.style.left = `${rect.left}px`
      el.style.top = `${rect.top}px`
      el.style.transform = "none"
      el.style.zIndex = String(++zCounter)
      return rect
    }

    const onPointerMove = (event) => {
      if (!state.dragging) return
      const nextLeft = state.startLeft + (event.clientX - state.startPointerX)
      const nextTop = state.startTop + (event.clientY - state.startPointerY)
      const maxLeft = Math.max(0, window.innerWidth - el.offsetWidth)
      const maxTop = Math.max(0, window.innerHeight - el.offsetHeight)

      el.style.left = `${clamp(nextLeft, 0, maxLeft)}px`
      el.style.top = `${clamp(nextTop, 0, maxTop)}px`
    }

    const endDrag = () => {
      if (!state.dragging) return
      state.dragging = false
      handle.style.cursor = "grab"
      window.removeEventListener("pointermove", onPointerMove)
      window.removeEventListener("pointerup", endDrag)
    }

    const onPointerDown = (event) => {
      if (window.innerWidth <= 700) return
      if (event.button !== 0) return
      if (event.target.closest("button, a, input, textarea, select, label")) return

      const rect = ensurePositioning()
      state.dragging = true
      state.startPointerX = event.clientX
      state.startPointerY = event.clientY
      state.startLeft = rect.left
      state.startTop = rect.top
      handle.style.cursor = "grabbing"

      window.addEventListener("pointermove", onPointerMove)
      window.addEventListener("pointerup", endDrag)
      event.preventDefault()
    }

    handle.addEventListener("pointerdown", onPointerDown)

    el._draggableModalCleanup = () => {
      handle.removeEventListener("pointerdown", onPointerDown)
      window.removeEventListener("pointermove", onPointerMove)
      window.removeEventListener("pointerup", endDrag)
    }
  },
  unmounted(el) {
    if (typeof el._draggableModalCleanup === "function") {
      el._draggableModalCleanup()
    }
  },
}
