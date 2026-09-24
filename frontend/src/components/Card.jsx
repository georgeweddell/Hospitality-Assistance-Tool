// The white box every section sits in, so padding, borders and headings match.
// `aside` sits to the right of the title (e.g. a small figure or a link).
function Card({ title, aside, className = '', flush = false, children }) {
  return (
    <section className={`rounded-xl border border-line bg-surface shadow-sm ${className}`}>
      {(title || aside) && (
        <div className="flex items-baseline justify-between gap-3 px-5 pt-4">
          {title && <h2 className="font-semibold text-ink">{title}</h2>}
          {aside && <div className="text-sm text-muted">{aside}</div>}
        </div>
      )}
      <div className={flush ? 'pt-3' : 'p-5 pt-4'}>{children}</div>
    </section>
  )
}

export default Card
