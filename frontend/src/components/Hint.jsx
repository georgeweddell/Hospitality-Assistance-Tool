import { useEffect, useRef, useState } from 'react'

// On-demand explanation. Shows on hover or keyboard focus, stays open when
// clicked (click again, press Escape or click elsewhere to close).
// Wrap an element to make it the trigger, or leave `children` out for an ⓘ icon.
function Hint({ content, children, label = 'More info', align = 'left' }) {
  const [open, setOpen] = useState(false)
  const [pinned, setPinned] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!pinned) return
    const onDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setPinned(false)
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [pinned])

  const toggle = (e) => {
    e.preventDefault()
    e.stopPropagation()   // inside clickable rows, don't also open the row
    setPinned(!pinned)
    setOpen(!pinned)
  }
  const close = () => {
    setPinned(false)
    setOpen(false)
  }

  return (
    <span
      ref={ref}
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => !pinned && setOpen(false)}
    >
      <button
        type="button"
        className={children ? 'hint-trigger' : 'hint-icon'}
        aria-label={children ? undefined : label}
        aria-expanded={open}
        onClick={toggle}
        onFocus={() => setOpen(true)}
        onBlur={() => !pinned && setOpen(false)}
        onKeyDown={(e) => e.key === 'Escape' && close()}
      >
        {children ?? 'i'}
      </button>
      {open && (
        <span role="tooltip" className={`hint-pop ${align === 'right' ? 'right-0' : 'left-0'}`}>
          {content}
        </span>
      )}
    </span>
  )
}

export default Hint
