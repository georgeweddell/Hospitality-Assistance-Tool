import { useState } from 'react'
import Card from './Card'
import QuadrantBadge from './QuadrantBadge'
import { percent, pounds } from '../format'

const COLUMNS = [
  { key: 'dish_name', label: 'Dish', align: 'left' },
  { key: 'category', label: 'Category', align: 'left' },
  { key: 'quadrant', label: 'Quadrant', align: 'left' },
  { key: 'menu_price', label: 'Price', format: pounds },
  { key: 'plate_cost', label: 'Plate cost', format: pounds },
  { key: 'margin_pounds', label: 'Margin', format: pounds },
  { key: 'margin_percent', label: 'Margin %', format: (v) => percent(v) },
  { key: 'units_sold', label: 'Units', format: String },
  { key: 'menu_mix_percent', label: 'Menu mix', format: (v) => percent(v) },
]

function DishTable({ dishes }) {
  const [sort, setSort] = useState({ key: null, desc: false })

  const sorted = sort.key
    ? [...dishes].sort((a, b) => {
        const x = a[sort.key]
        const y = b[sort.key]
        const cmp = typeof x === 'number' ? x - y : String(x).localeCompare(String(y))
        return sort.desc ? -cmp : cmp
      })
    : dishes

  const toggle = (key) =>
    setSort((s) => (s.key === key ? { key, desc: !s.desc } : { key, desc: typeof dishes[0]?.[key] === 'number' }))

  return (
    <Card title="Analysed dishes" aside={`${dishes.length} dishes`} flush>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-xs uppercase tracking-wide text-muted">
              {COLUMNS.map((col, i) => (
                <th
                  key={col.key}
                  className={`whitespace-nowrap py-2 font-medium ${col.align === 'left' ? 'text-left' : 'text-right'} ${
                    i === 0 ? 'pl-5 pr-3' : i === COLUMNS.length - 1 ? 'pl-3 pr-5' : 'px-3'
                  }`}
                  aria-sort={sort.key === col.key ? (sort.desc ? 'descending' : 'ascending') : undefined}
                >
                  <button type="button" onClick={() => toggle(col.key)} className="uppercase tracking-wide hover:text-ink">
                    {col.label}
                    <span className="ml-1 inline-block w-2">{sort.key === col.key ? (sort.desc ? '↓' : '↑') : ''}</span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((dish) => (
              <tr key={dish.dish_id} className="border-b border-line last:border-0">
                <td className="py-3 pl-5 pr-3">
                  <div className="whitespace-nowrap font-medium">{dish.dish_name}</div>
                  {dish.skipped_ingredients.length > 0 && (
                    <div className="text-xs text-warn">
                      {dish.skipped_ingredients.length} ingredient{dish.skipped_ingredients.length === 1 ? '' : 's'} not costed
                    </div>
                  )}
                </td>
                <td className="px-3 py-3 text-muted">{dish.category}</td>
                <td className="px-3 py-3"><QuadrantBadge quadrant={dish.quadrant} /></td>
                {COLUMNS.slice(3).map((col, i) => (
                  <td
                    key={col.key}
                    className={`whitespace-nowrap py-3 text-right tabular-nums ${i === COLUMNS.length - 4 ? 'pl-3 pr-5' : 'px-3'} ${
                      col.key === 'margin_pounds' ? 'font-medium' : ''
                    }`}
                  >
                    {col.format(dish[col.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

export default DishTable
