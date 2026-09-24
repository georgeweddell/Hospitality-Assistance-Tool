// The box every section sits in. `aside` sits to the right of the title
// (a small figure or a link). `flush` lets a table run edge to edge.
function Card({ title, aside, className = '', flush = false, children }) {
  return (
    <section className={`card ${flush ? 'overflow-hidden' : ''} ${className}`}>
      {(title || aside) && (
        <div className="card-header">
          {title && <h2 className="section-title">{title}</h2>}
          {aside && <div className="text-sm text-muted">{aside}</div>}
        </div>
      )}
      <div className={flush ? '' : title || aside ? 'card-body' : 'p-5'}>{children}</div>
    </section>
  )
}

export default Card
