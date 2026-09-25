import InvoiceReview from './InvoiceReview'
import MenuReview from './MenuReview'
import SalesReview from './SalesReview'

// The review screen for an upload ({ kind, review, options } from readUpload).
function ImportReview({ upload, onApplied, onCancel }) {
  const { kind, review, options } = upload
  if (kind === 'menu') return <MenuReview initial={review} onApplied={onApplied} onCancel={onCancel} />
  if (kind === 'invoice') return <InvoiceReview review={review} ingredients={options} onApplied={onApplied} onCancel={onCancel} />
  return <SalesReview initial={review} dishes={options} onApplied={onApplied} onCancel={onCancel} />
}

export default ImportReview
