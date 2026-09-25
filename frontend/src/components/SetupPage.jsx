import { useState } from 'react'
import Card from './Card'
import ImportReview from './ImportReview'
import QueueReview from './QueueReview'
import ReadingProgress from './ReadingProgress'
import RecipesTable from './RecipesTable'
import UploadButton from './UploadButton'
import { Tick } from './SetupChecklist'
import { navigate } from '../useHashRoute'
import { firstUnfinished, setupSteps } from '../setup'
import useUploadQueue from '../useUploadQueue'

// A new restaurant's path, one step at a time: menu, prices, recipes, sales,
// results. Prices come before recipes, so invoice ingredients (and their
// prices) are in the list when recipes are written. Each step reuses an
// existing screen: the import reviews and the Recipes table. Progress comes
// from the data itself (setup status), so leaving and coming back just works:
// there's no stored "wizard position".
const RAIL = [
  ['dishes', 'Menu'],
  ['prices', 'Your prices'],
  ['recipes', 'Recipes'],
  ['sales', 'Sales'],
  ['results', 'Results'],
]

function Figure({ label, value }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="label">{label}</p>
      <p className="stat-value num">{value}</p>
    </div>
  )
}

function SetupPage({ status, onChanged }) {
  const steps = Object.fromEntries(setupSteps(status).map((s) => [s.key, s]))
  const [step, setStep] = useState(() => firstUnfinished(status) ?? 'results')
  const [upload, setUpload] = useState(null)   // an upload being reviewed inside the step
  const [reading, setReading] = useState(null)
  const [error, setError] = useState(null)

  const go = (key) => {
    setUpload(null)
    setError(null)
    setStep(key)
  }
  const nextOf = (key) => RAIL[RAIL.findIndex(([k]) => k === key) + 1][0]
  const uploadProps = { reading, setReading, onError: setError, onRead: setUpload }
  // Invoices can be several at once; after the last one, move on to recipes.
  const queue = useUploadQueue(() => setStep('recipes'))

  // After an upload is applied: refresh the figures and move on.
  const applied = () => {
    const from = step
    setUpload(null)
    onChanged()
    setStep(nextOf(from))
  }

  let body
  if (queue.active) {
    body = <QueueReview queue={queue} onApplied={onChanged} />
  } else if (upload) {
    body = <ImportReview upload={upload} onApplied={applied} onCancel={() => setUpload(null)} />
  } else if (step === 'dishes') {
    body = (
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-6">
          <Figure label="Dishes on your menu" value={status.dishes} />
          <div className="flex flex-wrap items-center gap-3">
            <a href="#/menu" className="link text-sm">Add dishes by hand</a>
            <UploadButton kind="menu" label="Upload your menu" primary={status.dishes === 0} {...uploadProps} />
            {status.dishes > 0 && <button type="button" onClick={() => go('prices')} className="btn btn-primary">Next: Your prices</button>}
          </div>
        </div>
      </Card>
    )
  } else if (step === 'recipes') {
    body = (
      <div className="space-y-4">
        <RecipesTable onChanged={onChanged} />
        <div className="flex justify-end">
          <button type="button" onClick={() => go('sales')} className="btn btn-primary">Next: Sales</button>
        </div>
      </div>
    )
  } else if (step === 'prices') {
    body = (
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-6">
          <Figure label="Ingredients on your own prices" value={steps.prices.figure} />
          <div className="flex flex-wrap items-center gap-3">
            <a href="#/ingredients" className="link text-sm">Enter prices by hand</a>
            <UploadButton kind="invoice" label="Upload invoices" primary={!steps.prices.done} {...uploadProps}
                          onFiles={queue.start} multiple />
            <button type="button" onClick={() => go('recipes')} className={`btn ${steps.prices.done ? 'btn-primary' : 'btn-secondary'}`}>
              {steps.prices.done ? 'Next: Recipes' : 'Skip'}
            </button>
          </div>
        </div>
      </Card>
    )
  } else if (step === 'sales') {
    body = (
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-6">
          <Figure label="Sales" value={steps.sales.figure} />
          <div className="flex flex-wrap items-center gap-3">
            <a href="#/sales" className="link text-sm">Type totals by hand</a>
            <UploadButton kind="sales" label="Upload a till export" primary={!steps.sales.done} {...uploadProps} />
            {steps.sales.done && <button type="button" onClick={() => go('results')} className="btn btn-primary">Next: Results</button>}
          </div>
        </div>
      </Card>
    )
  } else {
    const missing = setupSteps(status).filter((s) => !s.optional && !s.done)
    body = (
      <Card>
        <div className="grid gap-6 sm:grid-cols-4">
          <Figure label="Dishes" value={status.dishes} />
          <Figure label="With a recipe" value={steps.recipes.figure} />
          <Figure label="Own prices" value={steps.prices.figure} />
          <Figure label="Sales" value={steps.sales.figure} />
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-end gap-3">
          {missing.map((s) => (
            <button key={s.key} type="button" onClick={() => go(s.key)} className="chip chip-warn">{s.label} to finish</button>
          ))}
          <button type="button" onClick={() => navigate('overview')} className="btn btn-primary">See your results</button>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <nav className="tabs" aria-label="Setup steps">
        {RAIL.map(([key, label], i) => (
          <button key={key} type="button" className="tab" aria-current={step === key ? 'page' : undefined} onClick={() => go(key)}>
            <Tick small done={key !== 'results' && steps[key].done} n={i + 1} />
            {label}
            {steps[key]?.optional && <span className="chip chip-muted">Optional</span>}
          </button>
        ))}
      </nav>
      {error && <p className="alert-error">{error}</p>}
      {reading && <ReadingProgress kind={reading} />}
      {body}
    </div>
  )
}

export default SetupPage
