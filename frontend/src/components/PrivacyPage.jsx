import PublicLayout from './PublicLayout'
import { CONTACT_EMAIL, LEGAL_UPDATED, OWNER } from '../legal'

// The privacy notice (UK GDPR) with the cookie section. Written from what the
// code actually stores: auth.py (the login cookie, accounts), the account
// folders (database, uploads, backups) and the sessionStorage keys. If any of
// those change, change this page and LEGAL_UPDATED in legal.js.

function Mail() {
  return <a href={`mailto:${CONTACT_EMAIL}`} className="link">{CONTACT_EMAIL}</a>
}

function PrivacyPage({ signedIn }) {
  return (
    <PublicLayout signedIn={signedIn}>
      <article className="doc">
        <h1 className="page-title">privacy &amp; cookies</h1>
        <p className="label">last updated {LEGAL_UPDATED}</p>

        <h2>who is responsible</h2>
        <p>
          Docket is run by {OWNER} as a personal portfolio project. {OWNER} is the controller of the personal
          data described here. Contact: <Mail />.
        </p>

        <h2>what we hold</h2>
        <ul>
          <li><strong>Your account:</strong> your email address, a scrambled (hashed) copy of your password that
            cannot be turned back into the password, and the date the account was created.</li>
          <li><strong>What you upload:</strong> menus, supplier invoices, till exports and anything you type in,
            plus everything Docket works out from them (dishes, recipes, prices, sales, reports). The original
            files are kept with your account.</li>
          <li><strong>Security records:</strong> failed sign-in counts by email address and by IP address, kept in
            the server's memory for 15 minutes. The hosting provider keeps request logs, which include IP
            addresses.</li>
        </ul>
        <p>
          Docket is for restaurant data. Please don't upload personal details about staff or customers that it
          doesn't need.
        </p>

        <h2>why, and on what basis</h2>
        <ul>
          <li><strong>To provide the service you signed up for</strong> (contract): your account, and storing and
            analysing your data.</li>
          <li><strong>To keep the service secure</strong> (legitimate interests): sign-in limits and request logs.</li>
        </ul>
        <p>Your data is not sold, not used for advertising and not used to train AI models by Docket.</p>

        <h2>who else handles it</h2>
        <ul>
          <li>
            <strong>Render</strong> hosts the site and stores all account data, on servers in Frankfurt, Germany.{' '}
            <a href="https://render.com/privacy" className="link" target="_blank" rel="noreferrer">Render's privacy policy</a>.
          </li>
          <li>
            <strong>Anthropic</strong> (Claude) processes the files and text you send to an AI feature: reading a
            menu, invoice or till export, estimating recipes, and writing reports. This means the data is sent to
            the United States. Anthropic processes it under its commercial terms.{' '}
            <a href="https://www.anthropic.com/legal/privacy" className="link" target="_blank" rel="noreferrer">Anthropic's privacy policy</a>.
          </li>
        </ul>
        <p>Nothing is shared with anyone else, unless the law requires it.</p>

        <h2>how long</h2>
        <p>
          Your data is kept while your account exists, including backups stored with it. Ask for your account to
          be deleted and everything in it (database, uploaded files, backups) is removed within 30 days.
        </p>

        <h2>your rights</h2>
        <p>
          You can ask for a copy of your data, for it to be corrected or deleted, or object to or restrict how it
          is used. Email <Mail />. If you're unhappy with the answer, you can complain to the Information
          Commissioner's Office (<a href="https://ico.org.uk/make-a-complaint/" className="link" target="_blank" rel="noreferrer">ico.org.uk</a>).
        </p>

        <h2>cookies and storage</h2>
        <p>
          Docket uses one cookie and your browser's session storage, only to make the site work. There are no
          analytics, advertising or third-party cookies, so there's nothing to accept or decline.
        </p>
        <div className="card overflow-x-auto">
          <table className="table">
            <thead>
              <tr><th>name</th><th>type</th><th>what it's for</th><th>how long</th></tr>
            </thead>
            <tbody>
              <tr><td className="num whitespace-nowrap">docket_session</td><td>cookie</td><td>Keeps you signed in. Your browser's scripts can't read it.</td><td>up to 7 days, or until you sign out</td></tr>
              <tr><td className="num whitespace-nowrap">analysis-range</td><td>session storage</td><td>The date range you chose.</td><td>until the tab closes</td></tr>
              <tr><td className="num whitespace-nowrap">menu-view</td><td>session storage</td><td>The menu page view you chose.</td><td>until the tab closes</td></tr>
              <tr><td className="num whitespace-nowrap">insights-category</td><td>session storage</td><td>The category you chose on insights.</td><td>until the tab closes</td></tr>
            </tbody>
          </table>
        </div>
        <p>Fonts are served by Docket itself, so opening the site contacts no other company.</p>

        <h2>changes</h2>
        <p>If this notice changes, the date at the top changes. Big changes are emailed to account holders.</p>
      </article>
    </PublicLayout>
  )
}

export default PrivacyPage
