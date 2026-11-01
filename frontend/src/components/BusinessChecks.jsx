import Hint from './Hint'

// The business suggestions tab of Reports: each check that fires as a row of one table
// (its figures, the target, then what to do), then the ones that pass as a single line.
// The rule of thumb in words lives in the hint, not in the table.
// Every figure is worked out in the backend (suggestions.py), formatted there.
function BusinessChecks({ checks }) {
  const firing = checks.filter((c) => c.fires)
  const passing = checks.filter((c) => !c.fires)

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-end gap-2">
        <span className="text-sm">
          <span className="num">{firing.length}</span> of <span className="num">{checks.length}</span> checks to look at
        </span>
      </div>

      {firing.length === 0 ? (
        <div className="empty">Every check passes</div>
      ) : (
        <section className="card">
          <div className="overflow-x-auto">
            <table className="table min-w-[720px]">
              <thead>
                <tr>
                  <th className="w-52">check</th>
                  <th>figures</th>
                  <th className="w-40">target</th>
                  <th className="w-64">action</th>
                </tr>
              </thead>
              <tbody>
                {firing.map((c) => (
                  <tr key={c.key}>
                    <td className="align-top">
                      <span className="font-semibold">{c.title}</span>{' '}
                      <Hint label={`About ${c.title}`}
                        content={c.rule_of_thumb ? `${c.note} Rule of thumb: ${c.rule_of_thumb}.` : c.note} />
                    </td>
                    <td className="align-top">
                      {c.figures.slice(0, 4).map((f) => (
                        <div key={f.label} className="flex flex-wrap items-baseline gap-x-2">
                          <span className="num">{f.display}</span>
                          <span className="text-[0.8125rem] text-muted">{f.label}</span>
                        </div>
                      ))}
                    </td>
                    <td className="align-top text-muted">{c.target}</td>
                    <td className="align-top font-semibold">{c.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {passing.length > 0 && (
        <p className="text-sm text-muted">
          passing · {passing.map((c) => c.title.toLowerCase()).join(' · ')}
        </p>
      )}
    </section>
  )
}

export default BusinessChecks
