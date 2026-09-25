import { useState } from 'react'
import Card from './Card'
import ConfirmDialog from './ConfirmDialog'
import Hint from './Hint'
import { postJson } from '../api'
import { navigate } from '../useHashRoute'

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

function SettingsPage({ onReset, onChanged }) {
  const [asking, setAsking] = useState(null)   // the option waiting for confirmation
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [backup, setBackup] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [synced, setSynced] = useState(null)

  // Adds new benchmark ingredients and records changed benchmark prices.
  // Nothing is removed, so no confirmation is needed.
  const updateBenchmarks = () => {
    setSyncing(true)
    setError(null)
    postJson('/setup/benchmarks', {})
      .then((result) => {
        setSynced(result)
        onChanged()
      })
      .catch((err) => setError(err.message))
      .finally(() => setSyncing(false))
  }

  const run = () => {
    setBusy(true)
    setError(null)
    postJson('/setup/reset', { mode: asking.mode, confirm: 'reset' })
      .then((result) => {
        setBackup(result.backup)
        setAsking(null)
        onReset()
        if (asking.mode === 'fresh') navigate('setup')   // a new restaurant starts with the guided setup
      })
      .catch((err) => {
        setError(err.message)
        setAsking(null)
      })
      .finally(() => setBusy(false))
  }

  return (
    <div className="max-w-2xl space-y-5">
      <Card title="Benchmark prices" flush>
        <div className="flex flex-wrap items-center gap-4 border-t border-line px-5 py-4">
          <span className="flex grow items-center gap-2 font-semibold">
            Update from the benchmark list
            <Hint label="About benchmark prices"
                  content="Adds any ingredients from the built-in UK price list that you don't have, and records changed benchmark prices. Your own prices and recipes are never changed." />
          </span>
          {synced && (
            <span className="flex flex-wrap gap-1.5">
              <span className="chip chip-accent num">{synced.added} added</span>
              <span className="chip chip-muted num">{synced.updated} updated</span>
              {synced.conflicts.length > 0 && (
                <Hint align="right" content={`Measured differently in your data, so left alone: ${synced.conflicts.join(', ')}.`}>
                  <span className="chip chip-warn num">{synced.conflicts.length} skipped</span>
                </Hint>
              )}
            </span>
          )}
          <button type="button" onClick={updateBenchmarks} disabled={syncing || busy} className="btn btn-secondary">
            {syncing ? 'Updating…' : 'Update'}
          </button>
        </div>
      </Card>

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
