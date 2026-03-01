import { useEffect, useRef } from 'react'

const escapeStack: Array<() => void> = []

if (typeof document !== 'undefined') {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && escapeStack.length > 0) {
      e.preventDefault()
      e.stopImmediatePropagation()
      const topHandler = escapeStack[escapeStack.length - 1]
      topHandler()
    }
  })
}

/**
 * Register a modal's close handler on a shared escape stack.
 * Only the topmost (most recently opened) modal closes on Escape.
 */
export function useEscapeStack(isOpen: boolean, onClose: () => void, disabled = false) {
  const closeRef = useRef(onClose)
  closeRef.current = onClose

  useEffect(() => {
    if (!isOpen || disabled) return
    const handler = () => closeRef.current()
    escapeStack.push(handler)
    return () => {
      const idx = escapeStack.indexOf(handler)
      if (idx >= 0) escapeStack.splice(idx, 1)
    }
  }, [isOpen, disabled])
}
