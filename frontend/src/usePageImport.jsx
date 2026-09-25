import { useState } from 'react'
import QueueReview from './components/QueueReview'
import UploadButton from './components/UploadButton'
import useUploadQueue from './useUploadQueue'

// An Import button for a page (Import menu on Menu, Import invoices on
// Ingredients, Import sales on Sales). Picking a file opens the same review
// screen as the Imports page, in place of the page; after Apply or Cancel the
// page comes back with fresh data.
//
//   const { button, review, error } = usePageImport('menu', 'Import menu', onChanged)
//   if (review) return review
export default function usePageImport(kind, label, onChanged, { multiple = false } = {}) {
  const [error, setError] = useState(null)
  const queue = useUploadQueue(onChanged)

  const button = (
    <UploadButton kind={kind} label={label} reading={null} setReading={() => {}} onError={setError}
                  onFiles={queue.start} multiple={multiple} />
  )
  const review = queue.active ? <QueueReview queue={queue} onApplied={onChanged} /> : null
  return { button, review, error }
}
