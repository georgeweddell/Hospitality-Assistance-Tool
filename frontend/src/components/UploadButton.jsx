import { useRef } from 'react'
import { UPLOADS, readUpload } from '../imports'

// A button that picks a file of one kind (menu, invoice, sales), uploads it and
// hands back what its review screen needs. `reading` is shared by the page's
// buttons, so only one file is read at a time.
function UploadButton({ kind, label, reading, setReading, onRead, onError, primary = false }) {
  const input = useRef(null)

  const pick = (e) => {
    const file = e.target.files[0]
    e.target.value = ''   // choosing the same file again still triggers a change
    if (!file) return
    setReading(kind)
    onError(null)
    readUpload(kind, file)
      .then(onRead)
      .catch((err) => onError(err.message))
      .finally(() => setReading(null))
  }

  return (
    <>
      <input ref={input} type="file" accept={UPLOADS[kind].accept} className="sr-only"
             onChange={pick} tabIndex={-1} aria-hidden="true" />
      <button type="button" onClick={() => input.current.click()} disabled={reading !== null}
              className={`btn ${primary ? 'btn-primary' : 'btn-secondary'}`}>
        {reading === kind ? UPLOADS[kind].reading : label}
      </button>
    </>
  )
}

export default UploadButton
