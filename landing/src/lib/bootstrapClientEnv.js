export function markJsEnabled(root = document.documentElement) {
  if (!(root instanceof HTMLElement)) return
  root.classList.add('js-enabled')
}
