import { useEffect, useState } from 'react'
import Card from './Card'
import { getJson, postJson } from '../api'
import { navigate } from '../useHashRoute'
import { rangeLabel, rangeQuery } from '../dateRange'
import { shortDate } from '../format'

// Reports written by the report agent (backend/report_agent.py). Starting one
// returns straight away; this page polls it each second, showing the trail of
// what Claude is looking at, then the report: next steps first, then findings.
// Every number on the page comes from a fact worked out by code (fact.display);
// Claude's own text has no numbers in it.

const POLL_MS = 1000

// Starts a report for the period (with the owner's optional focus) and opens it.
export function GenerateReportButton({ range, focus = '', className = '' }) {
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState(null)
  const start = () => {
    setStarting(true)
    setError(null)
    postJson(`/reports?${rangeQuery(range)}`, { focus: focus.trim() || null })
      .then((report) => navigate(`reports/${report.id}`))
      .catch((err) => {
        setError(err.message)
        setStarting(false)
      })
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-3">
      {error && <span className="text-sm text-danger">{error}</span>}
      <button type="button" onClick={start} disabled={starting} className={`btn btn-primary ${className}`}>
        {starting ? 'Starting…' : 'Generate report'}
      </button>
    </span>
  )
}

function periodOf(report) {
  return rangeLabel({ from: report.period_start, to: report.period_end })
}

// A cited fact: the number (formatted by code) over what it is; how it's worked out on hover.
function FactChip({ fact }) {
  return (
    <span className="flex min-w-0 flex-col gap-0.5 rounded-2xl border-[1.5px] border-ink bg-surface px-3 py-2"
          title={fact.note || undefined}>
      <span className="figure text-[1.5rem]">{fact.display}</span>
      <span className="font-mono text-[0.6875rem] leading-snug text-muted">{fact.label}</span>
    </span>
  )
}

function Item({ item, n, tone }) {
  return (
    <li className={`grid gap-4 p-6 md:grid-cols-[3rem_minmax(0,1fr)_minmax(0,0.9fr)] ${tone}`}>
      <span className="figure text-[2.5rem] leading-none">{String(n).padStart(2, '0')}</span>
      <div className="space-y-2">
        <h3 className="text-xl font-extrabold leading-tight tracking-tight">{item.title}</h3>
        <p className="leading-relaxed">{item.detail}</p>
      </div>
      <div className="flex flex-wrap content-start gap-2">
        {item.facts.map((f) => <FactChip key={f.id} fact={f} />)}
      </div>
    </li>
  )
}

// While the agent works: each tool call as a line, the latest one still going.
function Trail({ report, seconds }) {
  const steps = report.trail
  return (
    <div className="tile tile-outline gap-5 px-7 py-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <span className="figure text-[2.5rem]">writing · {periodOf(report).toLowerCase()}</span>
        <span className="tile-label num">{seconds} s</span>
      </div>
      <ol className="space-y-0">
        {steps.map((s, i) => {
          const latest = i === steps.length - 1
          return (
            <li key={i} className="flex items-center gap-4 border-t-[1.5px] border-dashed border-line-strong py-2.5 font-mono text-sm">
              <span className="w-6 text-muted">{String(i + 1).padStart(2, '0')}</span>
              <span className="grow">{s.label}</span>
              {latest ? (
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-line border-t-accent" aria-label="In progress" />
              ) : <span aria-label="Done">✓</span>}
            </li>
          )
        })}
        {steps.length === 0 && (
          <li className="flex items-center gap-4 border-t-[1.5px] border-dashed border-line-strong py-2.5 font-mono text-sm">
            <span className="w-6 text-muted">01</span>
            <span className="grow">Starting</span>
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-line border-t-accent" aria-label="In progress" />
          </li>
        )}
      </ol>
    </div>
  )
}

function Report({ report }) {
  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <h2 className="section-title text-[2rem]">next steps</h2>
        <ol className="overflow-hidden rounded-[22px] border-2 border-ink [&>li+li]:border-t-2 [&>li+li]:border-ink">
          {report.next_steps.map((item, i) => <Item key={i} item={item} n={i + 1} tone={i === 0 ? 'bg-mustard' : 'bg-surface'} />)}
        </ol>
      </section>
      <section className="space-y-4">
        <h2 className="section-title text-[2rem]">findings</h2>
        <ol className="overflow-hidden rounded-[22px] border-2 border-ink [&>li+li]:border-t-[1.5px] [&>li+li]:border-dashed [&>li+li]:border-line-strong">
          {report.findings.map((item, i) => <Item key={i} item={item} n={i + 1} tone="bg-surface" />)}
        </ol>
      </section>
    </div>
  )
}

// One report: polled while it's being written.
function ReportView({ id, range }) {
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    let ignore = false
    let timer
    const load = () => getJson(`/reports/${id}`)
      .then((r) => {
        if (ignore) return
        setReport(r)
        setNow(Date.now())
        if (r.status === 'running') timer = setTimeout(load, POLL_MS)
      })
      .catch((err) => { if (!ignore) setError(err.message) })
    load()
    return () => {
      ignore = true
      clearTimeout(timer)
    }
  }, [id])

  if (error) return <p className="alert-error">{error}</p>
  if (!report) return <p className="text-muted">Loading report…</p>

  const seconds = Math.max(0, Math.round((now - new Date(report.created_at).getTime()) / 1000))

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <p className="font-mono text-sm text-muted">
          <a href="#/reports" className="underline hover:text-ink print:hidden">reports</a>
          <span className="print:hidden"> / </span>
          {periodOf(report).toLowerCase()} · written {shortDate(report.created_at.slice(0, 10)).toLowerCase()}
        </p>
        {report.status === 'done' && (
          <button type="button" onClick={() => window.print()} className="btn btn-secondary print:hidden">Print or save as PDF</button>
        )}
      </div>

      {report.focus && (
        <p className="max-w-3xl font-mono text-sm">
          <span className="text-muted">focus · </span>{report.focus}
        </p>
      )}
      {report.status === 'running' && <Trail report={report} seconds={seconds} />}
      {report.status === 'failed' && (
        <div className="alert-error flex flex-wrap items-center justify-between gap-3">
          <span>{report.error}</span>
          {range && <GenerateReportButton range={range} focus={report.focus ?? ''} />}
        </div>
      )}
      {report.status === 'done' && <Report report={report} />}
    </div>
  )
}

// Past reports, newest first, and a new one for the chosen period.
function ReportList({ range }) {
  const [reports, setReports] = useState(null)
  const [focus, setFocus] = useState('')
  const [error, setError] = useState(null)

  useEffect(() => {
    let ignore = false
    getJson('/reports')
      .then((rows) => { if (!ignore) setReports(rows) })
      .catch((err) => { if (!ignore) setError(err.message) })
    return () => { ignore = true }
  }, [])

  return (
    <div className="space-y-5">
      {range && (
        <div className="tile tile-mustard corner-tr gap-5 px-7 py-6">
          <div className="flex flex-col gap-1.5">
            <span className="tile-label">new report</span>
            <span className="figure text-[3rem]">{rangeLabel(range).toLowerCase()}</span>
          </div>
          <label className="field">
            <span className="tile-label">any particular focus or question (optional)</span>
            <textarea value={focus} onChange={(e) => setFocus(e.target.value)} rows={2} maxLength={500}
                      placeholder="e.g. desserts, weekday trade, the mozzarella price"
                      className="input resize-y border-ink" />
          </label>
          <div className="flex justify-end">
            <GenerateReportButton range={range} focus={focus} className="bg-surface hover:bg-bg" />
          </div>
        </div>
      )}
      {error && <p className="alert-error">{error}</p>}
      {!reports ? (
        <p className="text-muted">Loading…</p>
      ) : reports.length === 0 ? (
        <div className="empty">No reports yet</div>
      ) : (
        <Card title="Past reports" flush>
          <table className="table">
            <thead>
              <tr><th>Period</th><th>Written</th><th>Status</th></tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id} className="row-link" onClick={() => navigate(`reports/${r.id}`)}>
                  <td><a href={`#/reports/${r.id}`} className="font-semibold hover:text-accent">{periodOf(r)}</a></td>
                  <td className="num">{shortDate(r.created_at.slice(0, 10))}</td>
                  <td>
                    <span className={`chip ${r.status === 'done' ? 'chip-accent' : r.status === 'running' ? 'chip-warn' : 'chip-muted'}`}>
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}

function ReportsPage({ id, range }) {
  return id ? <ReportView key={id} id={id} range={range} /> : <ReportList range={range} />
}

export default ReportsPage
