import { useEffect, useRef } from 'react'

// An in-page confirmation box for destructive actions. Used instead of the
// browser's window.confirm(), which some embedded browsers block (it then
// silently answers "Cancel"). Built on the native <dialog> element, which
// keeps keyboard focus inside while open and closes on Escape.
function ConfirmDialog({ open, title, children, confirmLabel, busy = false, onConfirm, onCancel }) {
  const ref = useRef(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      onCancel={(e) => {   // Escape key
        e.preventDefault()
        if (!busy) onCancel()
      }}
      className="m-auto w-[min(28rem,calc(100vw-2rem))] rounded-[14px] border border-line bg-surface p-0 text-ink shadow-xl backdrop:bg-ink/40"
    >
      <div className="space-y-3 p-6">
        <h2 className="section-title normal-case">{title}</h2>
        <div className="text-muted">{children}</div>
      </div>
      <div className="flex justify-end gap-2 border-t border-line bg-bg px-6 py-4">
        <button type="button" onClick={onCancel} disabled={busy} className="btn btn-secondary" autoFocus>Cancel</button>
        <button type="button" onClick={onConfirm} disabled={busy} className="btn btn-primary">
          {busy ? 'Working…' : confirmLabel}
        </button>
      </div>
    </dialog>
  )
}

export default ConfirmDialog
