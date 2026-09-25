import { useRef } from 'react'
import { UPLOADS, readUpload } from '../imports'

// A button that picks a file of one kind (menu, invoice, sales), uploads it and
// hands back what its review screen needs. `reading` is shared by the page's
// buttons, so only one file is read at a time. With `onFiles`, the picked
// files are handed over unread (for a useUploadQueue); `multiple` allows several.
function UploadButton({ kind, label, reading, setReading, onRead, onError, onFiles, multiple = false, primary = false }) {
  const input = useRef(null)

  const pick = (e) => {
    const files = [...e.target.files]
    e.target.value = ''   // choosing the same file again still triggers a change
    if (files.length === 0) return
    if (onFiles) {
      onError(null)
      onFiles(kind, files)
      return
    }
    const file = files[0]
    setReading(kind)
    onError(null)
    readUpload(kind, file)
      .then(onRead)
      .catch((err) => onError(err.message))
      .finally(() => setReading(null))
  }

  return (
    <>
      <input ref={input} type="file" accept={UPLOADS[kind].accept} multiple={multiple} className="sr-only"
             onChange={pick} tabIndex={-1} aria-hidden="true" />
      <button type="button" onClick={() => input.current.click()} disabled={reading !== null}
              className={`btn ${primary ? 'btn-primary' : 'btn-secondary'}`}>
        {reading === kind ? UPLOADS[kind].reading : label}
      </button>
    </>
  )
}

export default UploadButton
