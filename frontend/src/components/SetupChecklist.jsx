import Hint from './Hint'
import { navigate } from '../useHashRoute'
import { setupSteps } from '../setup'

// small: for the Setup page's step rail.
export function Tick({ done, n, small = false }) {
  const size = small ? 'h-5 w-5 text-xs' : 'h-7 w-7 text-sm'
  return done ? (
    <span className={`flex ${size} shrink-0 items-center justify-center rounded-full bg-accent text-accent-ink`} aria-label="Done">
      <svg viewBox="0 0 24 24" className={small ? 'h-3 w-3' : 'h-4 w-4'} fill="none" stroke="currentColor" strokeWidth="3"
           strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10" /></svg>
    </span>
  ) : (
    <span className={`num flex ${size} shrink-0 items-center justify-center rounded-full border-2 border-line-strong font-semibold text-muted`}>
      {n}
    </span>
  )
}

// Setup progress on the Overview, until the required steps are done. The work
// itself happens on the Setup page, which opens at the first unfinished step.
function SetupChecklist({ status }) {
  const steps = setupSteps(status)
  const required = steps.filter((s) => !s.optional)
  const done = required.filter((s) => s.done).length

  return (
    <section className="card">
      <div className="card-header">
        <h2 className="section-title">Set up</h2>
        <span className="flex items-center gap-3">
          <span className="count num">{done} / {required.length}</span>
          <button type="button" onClick={() => navigate('setup')} className="btn btn-primary btn-sm">Continue setup</button>
        </span>
      </div>
      <ol>
        {steps.map((s, i) => (
          <li key={s.key} className="flex items-center gap-4 border-t border-line px-5 py-3.5">
            <Tick done={s.done} n={i + 1} />
            <span className="flex grow items-center gap-2 font-semibold">
              {s.label}
              {s.optional && <span className="chip chip-muted">Optional</span>}
              {s.hint && <Hint content={s.hint} label={`About ${s.label}`} />}
            </span>
            <span className="num w-20 text-right text-muted">{s.figure}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}

export default SetupChecklist
