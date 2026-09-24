import { useState } from 'react'
import Card from './Card'
import ConfirmDialog from './ConfirmDialog'
import Hint from './Hint'
import { postJson } from '../api'

const OPTIONS = [
  {
    mode: 'fresh',
    label: 'Start fresh',
    button: 'btn-danger',
    hint: 'Removes every dish, recipe, sale and price you have entered. Keeps the benchmark ingredient list.',
    confirmTitle: 'Start fresh?',
    confirmBody: 'Every dish, recipe, sale and price you have entered will be removed. The current database is backed up first.',
  },
  {
    mode: 'demo',
    label: 'Load demo data',
    button: 'btn-secondary',
    hint: 'Replaces everything with the demo pizzeria: 22 dishes and three months of daily sales.',
    confirmTitle: 'Load the demo pizzeria?',
    confirmBody: 'Everything currently entered will be replaced. The current database is backed up first.',
  },
]

function SettingsPage({ onReset }) {
  const [asking, setAsking] = useState(null)   // the option waiting for confirmation
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [backup, setBackup] = useState(null)

  const run = () => {
    setBusy(true)
    setError(null)
    postJson('/setup/reset', { mode: asking.mode, confirm: 'reset' })
      .then((result) => {
        setBackup(result.backup)
        setAsking(null)
        onReset()
      })
      .catch((err) => {
        setError(err.message)
        setAsking(null)
      })
      .finally(() => setBusy(false))
  }

  return (
    <div className="max-w-2xl space-y-5">
      <Card title="Data" flush>
        <ul>
          {OPTIONS.map((o) => (
            <li key={o.mode} className="flex items-center gap-4 border-t border-line px-5 py-4">
              <span className="flex grow items-center gap-2 font-semibold">
                {o.label}
                <Hint content={o.hint} label={`About ${o.label}`} />
              </span>
              <button type="button" onClick={() => setAsking(o)} disabled={busy} className={`btn ${o.button}`}>
                {o.label}
              </button>
            </li>
          ))}
        </ul>
      </Card>
      {backup && (
        <Hint content={`The previous database was saved as backend/${backup}.`}>
          <span className="chip chip-accent">Backup saved</span>
        </Hint>
      )}
      {error && <p className="alert-error">{error}</p>}

      <ConfirmDialog
        open={asking !== null}
        title={asking?.confirmTitle}
        confirmLabel={asking?.label}
        busy={busy}
        onConfirm={run}
        onCancel={() => setAsking(null)}
      >
        {asking?.confirmBody}
      </ConfirmDialog>
    </div>
  )
}

export default SettingsPage
