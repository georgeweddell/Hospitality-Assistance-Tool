import { priceForDisplay } from '../format'
import { PACK_UNITS } from '../prices'

const INPUT = 'w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus:border-accent focus:outline-none'

// "Paid £93.60 for 12 kg" plus where the price came from. Shows the price per
// kg / l / each as a preview while typing.
function PriceFields({ unit, price, onChange }) {
  const set = (field) => (e) => onChange({ ...price, [field]: e.target.value })
  const options = PACK_UNITS[unit]
  const factor = options.find(([u]) => u === price.packUnit)?.[1] ?? 1
  const perBase = Number(price.packPrice) / (Number(price.packQuantity) * factor)

  return (
    <div className="grid gap-3 sm:grid-cols-[1fr_1fr_1fr]">
      <label className="text-sm">
        <span className="mb-1 block text-muted">Paid (£)</span>
        <input type="number" min="0" step="0.01" value={price.packPrice} onChange={set('packPrice')}
               className={INPUT} placeholder="93.60" />
      </label>
      <label className="text-sm">
        <span className="mb-1 block text-muted">For</span>
        <div className="flex gap-2">
          <input type="number" min="0" step="any" value={price.packQuantity} onChange={set('packQuantity')}
                 className={`${INPUT} text-right`} />
          <select value={price.packUnit} onChange={set('packUnit')} className={`${INPUT} w-24`}>
            {options.map(([u]) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
      </label>
      <label className="text-sm">
        <span className="mb-1 block text-muted">From</span>
        <select value={price.source} onChange={set('source')} className={INPUT}>
          <option value="invoice">Invoice</option>
          <option value="supplier_list">Supplier price list</option>
          <option value="manual">Other / my estimate</option>
        </select>
      </label>
      <label className="text-sm sm:col-span-2">
        <span className="mb-1 block text-muted">Supplier (optional)</span>
        <input type="text" value={price.supplier} onChange={set('supplier')} className={INPUT} />
      </label>
      <div className="self-end pb-2 text-sm text-muted">
        {Number.isFinite(perBase) && perBase >= 0 && Number(price.packPrice) > 0 ? (
          <>= <span className="font-semibold tabular-nums text-ink">{priceForDisplay(perBase, unit)}</span></>
        ) : null}
      </div>
    </div>
  )
}

export default PriceFields
