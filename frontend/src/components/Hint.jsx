import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

const GAP = 8      // space between the trigger and the popover
const MARGIN = 8   // keep the popover this far inside the window

// On-demand explanation. Shows on hover or keyboard focus, stays open when
// clicked (click again, press Escape or click elsewhere to close).
// Wrap an element to make it the trigger, or leave `children` out for an ⓘ icon.
//
// The popover is drawn at the top level of the page (a portal), not inside the
// card, so cards and scrolling tables can't clip it. It's positioned from the
// trigger's place on screen: below it, or above if there's no room, and kept
// inside the window.
function Hint({ content, children, label = 'More info', align = 'left' }) {
  const [open, setOpen] = useState(false)
  const [pinned, setPinned] = useState(false)
  const [position, setPosition] = useState(null)
  const triggerRef = useRef(null)
  const popRef = useRef(null)

  const close = () => {
    setPinned(false)
    setOpen(false)
  }

  // Place the popover once it's rendered and its size is known.
  useLayoutEffect(() => {
    if (!open || !triggerRef.current || !popRef.current) return
    const t = triggerRef.current.getBoundingClientRect()
    const p = popRef.current.getBoundingClientRect()
    // The visible area, excluding scrollbars (window.innerWidth includes them).
    const viewWidth = document.documentElement.clientWidth
    const viewHeight = document.documentElement.clientHeight
    let top = t.bottom + GAP
    if (top + p.height > viewHeight - MARGIN) top = Math.max(MARGIN, t.top - GAP - p.height)
    let left = align === 'right' ? t.right - p.width : t.left
    left = Math.min(Math.max(MARGIN, left), viewWidth - p.width - MARGIN)
    setPosition({ top, left })
  }, [open, align, content])

  // While open: close on scroll or resize (it would drift from its trigger),
  // and, when pinned, on a click anywhere else.
  useEffect(() => {
    if (!open) return
    const onMove = () => close()
    const onDown = (e) => {
      if (!pinned) return
      if (triggerRef.current?.contains(e.target) || popRef.current?.contains(e.target)) return
      close()
    }
    window.addEventListener('scroll', onMove, true)
    window.addEventListener('resize', onMove)
    document.addEventListener('mousedown', onDown)
    return () => {
      window.removeEventListener('scroll', onMove, true)
      window.removeEventListener('resize', onMove)
      document.removeEventListener('mousedown', onDown)
    }
  }, [open, pinned])

  const show = () => {
    setPosition(null)
    setOpen(true)
  }

  const toggle = (e) => {
    e.preventDefault()
    e.stopPropagation()   // inside clickable rows, don't also open the row
    if (pinned) {
      close()
    } else {
      setPinned(true)
      if (!open) show()
    }
  }

  return (
    <span
      className="inline-flex"
      onMouseEnter={() => !open && show()}
      onMouseLeave={() => !pinned && setOpen(false)}
    >
      <button
        ref={triggerRef}
        type="button"
        className={children ? 'hint-trigger' : 'hint-icon'}
        aria-label={children ? undefined : label}
        aria-expanded={open}
        onClick={toggle}
        onFocus={() => !open && show()}
        onBlur={() => !pinned && setOpen(false)}
        onKeyDown={(e) => e.key === 'Escape' && close()}
      >
        {children ?? 'i'}
      </button>
      {open && createPortal(
        <span
          ref={popRef}
          role="tooltip"
          className="hint-pop"
          style={position ? { top: position.top, left: position.left } : { top: 0, left: 0, visibility: 'hidden' }}
        >
          {content}
        </span>,
        document.body,
      )}
    </span>
  )
}

export default Hint
