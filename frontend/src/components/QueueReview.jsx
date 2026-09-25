import ImportReview from './ImportReview'
import ReadingProgress from './ReadingProgress'

const NOUN = { invoice: 'Invoice', menu: 'Menu', sales: 'File' }

// The file a useUploadQueue is on: still being read, couldn't be read, or
// ready to review. Apply and Cancel both move on to the next file.
function QueueReview({ queue, onApplied }) {
  const { current, kind, position, total } = queue
  return (
    <div className="space-y-4">
      {total > 1 && <p className="label num">{NOUN[kind]} {position} of {total}</p>}
      {current === null && <ReadingProgress key={position} kind={kind} />}
      {current?.error && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="alert-error grow">{current.error}</p>
          <button type="button" onClick={queue.next} className="btn btn-secondary">
            {position < total ? 'Skip' : 'Close'}
          </button>
        </div>
      )}
      {current?.upload && (
        <ImportReview key={position} upload={current.upload}
                      onApplied={(record) => { onApplied(record); queue.next() }}
                      onCancel={queue.next} />
      )}
    </div>
  )
}

export default QueueReview
