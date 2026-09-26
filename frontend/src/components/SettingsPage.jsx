import { useEffect, useState } from 'react'
import Card from './Card'
import ConfirmDialog from './ConfirmDialog'
import Hint from './Hint'
import { getJson, postJson, putJson } from '../api'
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

const TYPE_LABELS = { pizzeria: 'Pizzeria', gastropub: 'Gastropub', cafe: 'Café', indian: 'Indian', other: 'Other' }

// The restaurant's type: picks the rules of thumb the business checks use
// (backend/data/business_rules.csv).
function RestaurantType({ onChanged }) {
  const [business, setBusiness] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    getJson('/settings/business').then(setBusiness).catch((err) => setError(err.message))
  }, [])
  const choose = (restaurantType) =>
    putJson('/settings/business', { restaurant_type: restaurantType })
      .then((b) => { setBusiness(b); onChanged() })
      .catch((err) => setError(err.message))

  return (
    <Card title="Restaurant" flush>
      <div className="flex flex-wrap items-center gap-4 border-t border-line px-5 py-4">
        <span className="flex grow items-center gap-2 font-semibold">
          Type of restaurant
          <Hint label="About the type" content="Picks the rules of thumb the business checks on Insights are judged against, such as the usual food cost for this kind of restaurant." />
        </span>
        {error && <span className="text-sm text-danger">{error}</span>}
        {business && (
          <select value={business.restaurant_type} onChange={(e) => choose(e.target.value)}
                  className="input input-pill w-auto" aria-label="Type of restaurant">
            {business.types.map((t) => <option key={t} value={t}>{TYPE_LABELS[t] ?? t}</option>)}
          </select>
        )}
      </div>
    </Card>
  )
}

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
      <RestaurantType onChanged={onChanged} />
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
