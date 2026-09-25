import { useEffect, useState } from 'react'
import { UPLOADS, readingPercent } from '../imports'

// A progress bar while Claude reads an uploaded file. Claude doesn't report
// progress, so the bar is timed against how long this kind of file usually
// takes (see readingPercent), with the seconds so far shown alongside.
// Render it only while reading, so each read starts from zero.
function ReadingProgress({ kind }) {
  const { reading, seconds } = UPLOADS[kind]
  const [started] = useState(() => Date.now())
  const [now, setNow] = useState(started)

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 250)
    return () => clearInterval(timer)
  }, [])

  const elapsed = (now - started) / 1000
  return (
    <div className="card space-y-2.5 px-5 py-4" role="status" aria-live="polite">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-semibold">{reading}</span>
        <span className="num text-muted">{Math.floor(elapsed)} s</span>
      </div>
      <div className="progress" role="progressbar" aria-label={reading}
           aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(readingPercent(elapsed, seconds))}>
        <div className="progress-bar" style={{ width: `${readingPercent(elapsed, seconds)}%` }} />
      </div>
    </div>
  )
}

export default ReadingProgress
