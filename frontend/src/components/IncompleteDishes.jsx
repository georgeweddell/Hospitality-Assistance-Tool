import Card from './Card'

function IncompleteDishes({ items }) {
  if (items.length === 0) return null

  return (
    <Card title="Not yet analysed" aside={`${items.length} dishes`} flush>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <th className="py-2 pl-5 pr-3 font-medium">Dish</th>
              <th className="px-3 py-2 font-medium">Category</th>
              <th className="py-2 pl-3 pr-5 font-medium">Missing</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.dish_id} className="border-b border-line last:border-0">
                <td className="py-3 pl-5 pr-3 font-medium">{item.dish_name}</td>
                <td className="px-3 py-3 text-muted">{item.category || '—'}</td>
                <td className="py-3 pl-3 pr-5">
                  <div className="flex flex-wrap gap-1.5">
                    {item.reasons.map((r) => (
                      <span key={r} className="rounded-full bg-warn-bg px-2 py-0.5 text-xs text-warn">
                        {r.replace(/^No /, '').replace(/^\w/, (c) => c.toUpperCase())}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

export default IncompleteDishes
