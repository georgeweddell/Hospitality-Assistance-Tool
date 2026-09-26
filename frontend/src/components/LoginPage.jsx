import { useState } from 'react'
import { postJson, setToken } from '../api'

// Signing in (backend: auth.py): sign in, create an account with the invite
// code, or try the demo (a private guest copy of the demo pizzeria).
function LoginPage({ onSignedIn }) {
  const [mode, setMode] = useState('signin')   // signin | signup
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [invite, setInvite] = useState('')
  const [busy, setBusy] = useState(null)       // 'form' | 'demo' while waiting
  const [error, setError] = useState(null)

  const done = (result) => {
    setToken(result.token)
    window.location.hash = '#/overview'
    onSignedIn(result.account)
  }
  const fail = (err) => {
    setError(err.message)
    setBusy(null)
  }

  const submit = (e) => {
    e.preventDefault()
    setBusy('form')
    setError(null)
    const request = mode === 'signin'
      ? postJson('/auth/login', { email, password })
      : postJson('/auth/signup', { email, password, invite_code: invite })
    request.then(done).catch(fail)
  }

  const tryDemo = () => {
    setBusy('demo')
    setError(null)
    postJson('/auth/demo').then(done).catch(fail)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4 py-10 text-ink">
      <div className="w-full max-w-md space-y-6">
        <p className="text-center text-[56px] font-extrabold leading-none tracking-[-0.04em]">
          docket<span className="text-accent">.</span>
        </p>

        <form onSubmit={submit} className="card space-y-4 p-6">
          <div className="segmented w-full" role="group" aria-label="Sign in or create an account">
            <button type="button" className="flex-1" aria-pressed={mode === 'signin'} onClick={() => setMode('signin')}>sign in</button>
            <button type="button" className="flex-1" aria-pressed={mode === 'signup'} onClick={() => setMode('signup')}>create account</button>
          </div>
          <label className="field">
            <span className="label">email</span>
            <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input" />
          </label>
          <label className="field">
            <span className="label">password</span>
            <input type="password" required minLength={mode === 'signup' ? 8 : undefined}
                   autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                   value={password} onChange={(e) => setPassword(e.target.value)} className="input" />
          </label>
          {mode === 'signup' && (
            <label className="field">
              <span className="label">invite code</span>
              <input required value={invite} onChange={(e) => setInvite(e.target.value)} className="input" />
            </label>
          )}
          {error && <p className="alert-error">{error}</p>}
          <button type="submit" disabled={busy !== null} className="btn btn-secondary w-full">
            {busy === 'form' ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <button type="button" onClick={tryDemo} disabled={busy !== null} className="btn btn-primary w-full py-4 text-sm">
          {busy === 'demo' ? 'Setting up the demo…' : 'Try the demo'}
        </button>
      </div>
    </div>
  )
}

export default LoginPage
