import { priceForDisplay } from '../format'
import { PACK_UNITS } from '../prices'

// "Paid £93.60 for 12 kg" plus where the price came from. Shows the price per
// kg / l / each as a preview while typing (the backend does the real conversion).
function PriceFields({ unit, price, onChange }) {
  const set = (field) => (e) => onChange({ ...price, [field]: e.target.value })
  const options = PACK_UNITS[unit]
  const factor = options.find(([u]) => u === price.packUnit)?.[1] ?? 1
  const perBase = Number(price.packPrice) / (Number(price.packQuantity) * factor)

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="field">
        <span className="label">Paid (£)</span>
        <input type="number" min="0" step="0.01" value={price.packPrice} onChange={set('packPrice')}
               className="input num" placeholder="93.60" />
      </label>
      <label className="field">
        <span className="label">For</span>
        <div className="flex gap-2">
          <input type="number" min="0" step="any" value={price.packQuantity} onChange={set('packQuantity')}
                 className="input num text-right" aria-label="Quantity" />
          <select value={price.packUnit} onChange={set('packUnit')} className="input w-24" aria-label="Unit">
            {options.map(([u]) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
      </label>
      <label className="field">
        <span className="label">From</span>
        <select value={price.source} onChange={set('source')} className="input">
          <option value="invoice">Invoice</option>
          <option value="supplier_list">Supplier price list</option>
          <option value="manual">Other / my estimate</option>
        </select>
      </label>
      <label className="field sm:col-span-2">
        <span className="label">Supplier</span>
        <input type="text" value={price.supplier} onChange={set('supplier')} className="input" placeholder="Optional" />
      </label>
      <div className="flex items-end pb-2">
        {Number.isFinite(perBase) && perBase >= 0 && Number(price.packPrice) > 0 && (
          <p className="num text-muted">
            = <span className="font-display text-lg font-semibold text-ink">{priceForDisplay(perBase, unit)}</span>
          </p>
        )}
      </div>
    </div>
  )
}

export default PriceFields
