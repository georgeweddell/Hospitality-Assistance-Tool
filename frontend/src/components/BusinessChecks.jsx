import Hint from './Hint'

// The business suggestions tab of Reports: each check that fires as a card (its figures
// beside the target, then what to do), then the ones that pass as a single line.
// The rule of thumb in words lives in the hint, not on the card.
// Every figure is worked out in the backend (suggestions.py), formatted there.
function BusinessChecks({ checks }) {
  const firing = checks.filter((c) => c.fires)
  const passing = checks.filter((c) => !c.fires)

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-end gap-2">
        <span className="font-mono text-sm">{firing.length} of {checks.length} checks to look at</span>
      </div>

      {firing.length === 0 ? (
        <div className="empty">Every check passes</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {firing.map((c) => (
            <article key={c.key} className="card flex flex-col gap-3 p-5">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-lg font-extrabold leading-tight tracking-tight">{c.title}</h3>
                <Hint align="right" label={`About ${c.title}`}
                  content={c.rule_of_thumb ? `${c.note} Rule of thumb: ${c.rule_of_thumb}.` : c.note} />
              </div>
              <div className="flex flex-wrap gap-2">
                {c.figures.slice(0, 4).map((f) => (
                  <span key={f.label} className="flex min-w-0 flex-col rounded-2xl border-[1.5px] border-ink px-3 py-1.5">
                    <span className="figure text-[1.375rem]">{f.display}</span>
                    <span className="font-mono text-[0.6875rem] leading-snug text-muted">{f.label}</span>
                  </span>
                ))}
                {c.target && (
                  <span className="flex min-w-0 flex-col rounded-2xl border-[1.5px] border-dashed border-ink px-3 py-1.5">
                    <span className="figure text-[1.375rem]">{c.target}</span>
                    <span className="font-mono text-[0.6875rem] leading-snug text-muted">target</span>
                  </span>
                )}
              </div>
              <p className="mt-auto font-semibold">{c.action}</p>
            </article>
          ))}
        </div>
      )}

      {passing.length > 0 && (
        <p className="font-mono text-sm text-muted">
          passing · {passing.map((c) => c.title.toLowerCase()).join(' · ')}
        </p>
      )}
    </section>
  )
}

export default BusinessChecks
