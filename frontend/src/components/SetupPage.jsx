import { useState } from 'react'
import ImportReview from './ImportReview'
import QueueReview from './QueueReview'
import ReadingProgress from './ReadingProgress'
import RecipesTable from './RecipesTable'
import UploadButton from './UploadButton'
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
  ['dishes', 'menu'],
  ['prices', 'your prices'],
  ['recipes', 'recipes'],
  ['sales', 'sales'],
  ['results', 'results'],
]

// What each upload step shows: its colour (as on the Imports page), the figure
// label, the upload, and the way to do it by hand.
const UPLOAD_STEPS = {
  dishes: { tone: 'tile-mustard corner-tr', label: 'dishes on your menu', kind: 'menu', upload: 'Upload your menu',
            formats: 'pdf · photo', byHand: ['#/menu', 'add dishes by hand'] },
  prices: { tone: 'tile-tomato', label: 'ingredients on your own prices', kind: 'invoice', upload: 'Upload invoices',
            formats: 'pdf · photo · several', byHand: ['#/ingredients', 'enter prices by hand'] },
  sales: { tone: 'tile-basil corner-tl', label: 'sales', kind: 'sales', upload: 'Upload a till export',
           formats: 'csv till export', byHand: ['#/sales', 'type totals by hand'] },
}

const Check = () => (
  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="3"
       strokeLinecap="round" strokeLinejoin="round" aria-label="Done"><path d="M5 12l5 5 9-10" /></svg>
)

// One step in the rail: ink and raised when open (like the current nav pill),
// basil when done, outlined when still to do.
function StepTile({ n, label, figure, done, optional, current, onClick }) {
  const tone = current ? 'bg-ink text-bg -translate-y-1' : done ? 'tile-basil' : 'tile-outline'
  return (
    <button type="button" onClick={onClick} aria-current={current ? 'step' : undefined}
            className={`tile min-h-[124px] cursor-pointer gap-2 px-4 py-3.5 text-left transition-transform ${tone}`}>
      <span className="flex items-center justify-between">
        <span className="tile-label">{String(n).padStart(2, '0')}{optional && ' · optional'}</span>
        {done && <Check />}
      </span>
      <span className="figure text-[1.875rem]">{label}</span>
      <span className="tile-label num">{figure ?? ' '}</span>
    </button>
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
  const labelOf = (key) => RAIL.find(([k]) => k === key)[1]
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

  // Next is offered once a step is done; the optional prices step can be skipped.
  const next = (key, label = `Next: ${labelOf(nextOf(key))}`) => (
    <div className="flex justify-end">
      <button type="button" onClick={() => go(nextOf(key))} className="btn btn-primary">{label} →</button>
    </div>
  )

  let body
  if (queue.active) {
    body = <QueueReview queue={queue} onApplied={onChanged} />
  } else if (upload) {
    body = <ImportReview upload={upload} onApplied={applied} onCancel={() => setUpload(null)} />
  } else if (UPLOAD_STEPS[step]) {
    const u = UPLOAD_STEPS[step]
    const figure = step === 'dishes' ? String(status.dishes) : steps[step].figure
    body = (
      <div className="space-y-5">
        <div className={`tile min-h-[240px] flex-row flex-wrap items-end gap-8 px-8 py-7 ${u.tone}`}>
          <div className="flex flex-col gap-3">
            <span className="tile-label">{u.label}</span>
            <span className="figure text-[clamp(5rem,10vw,8.5rem)] leading-[0.8]">{figure.toLowerCase()}</span>
          </div>
          <div className="flex flex-col items-start gap-3">
            <UploadButton kind={u.kind} label={u.upload} {...uploadProps}
                          onFiles={u.kind === 'invoice' ? queue.start : undefined} multiple={u.kind === 'invoice'}
                          className="border-current px-6 py-3.5 text-sm text-inherit hover:bg-surface/20" />
            <span className="tile-label">{u.formats} · <a href={u.byHand[0]} className="underline">{u.byHand[1]}</a></span>
          </div>
        </div>
        {step === 'prices' ? next('prices', steps.prices.done ? undefined : 'Skip') : steps[step].done && next(step)}
      </div>
    )
  } else if (step === 'recipes') {
    body = status.dishes === 0 ? (
      <div className="empty">
        No dishes yet
        <button type="button" onClick={() => go('dishes')} className="link ml-2">Menu</button>
      </div>
    ) : (
      <div className="space-y-5">
        <RecipesTable onChanged={onChanged} />
        {next('recipes')}
      </div>
    )
  } else {
    const missing = setupSteps(status).filter((s) => !s.optional && !s.done)
    body = (
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="tile tile-mustard corner-tr min-h-[140px]">
            <span className="tile-label">dishes</span><span className="figure text-[3.5rem]">{status.dishes}</span>
          </div>
          <div className="tile tile-outline min-h-[140px]">
            <span className="tile-label">with a recipe</span><span className="figure text-[3.5rem]">{steps.recipes.figure}</span>
          </div>
          <div className="tile tile-tomato min-h-[140px]">
            <span className="tile-label">own prices</span><span className="figure text-[3.5rem]">{steps.prices.figure}</span>
          </div>
          <div className="tile tile-basil corner-tl min-h-[140px]">
            <span className="tile-label">sales</span><span className="figure text-[3.5rem]">{steps.sales.figure.toLowerCase()}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-3">
          {missing.map((s) => (
            <button key={s.key} type="button" onClick={() => go(s.key)} className="chip chip-warn">{s.label} to finish</button>
          ))}
          <button type="button" onClick={() => navigate('overview')} className="btn btn-primary">See your results →</button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-7">
      <nav className="grid grid-cols-2 gap-3 pt-1 sm:grid-cols-3 lg:grid-cols-5" aria-label="Setup steps">
        {RAIL.map(([key, label], i) => (
          <StepTile key={key} n={i + 1} label={label} current={step === key} onClick={() => go(key)}
                    done={key !== 'results' && steps[key].done} optional={steps[key]?.optional}
                    figure={key === 'results' ? null : steps[key].figure} />
        ))}
      </nav>
      {error && <p className="alert-error">{error}</p>}
      {reading && <ReadingProgress kind={reading} />}
      {body}
    </div>
  )
}

export default SetupPage
