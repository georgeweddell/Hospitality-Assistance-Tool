import PublicLayout from './PublicLayout'
import { CONTACT_EMAIL, LEGAL_UPDATED, OWNER } from '../legal'

// Terms of use. Not legally required for a free site, but they say plainly what
// Docket is (a portfolio demo), that its figures and AI output need checking,
// and that it comes with no guarantees.

function TermsPage({ signedIn }) {
  return (
    <PublicLayout signedIn={signedIn}>
      <article className="doc">
        <h1 className="page-title">terms of use</h1>
        <p className="label">last updated {LEGAL_UPDATED}</p>

        <h2>what docket is</h2>
        <p>
          Docket is a free portfolio project run by {OWNER}. Accounts are by invite. By creating an account or
          using the site you agree to these terms. The <a href="#/privacy" className="link">privacy notice</a>{' '}
          explains how your data is handled.
        </p>

        <h2>your account</h2>
        <ul>
          <li>Keep your password to yourself. You're responsible for what's done with your account.</li>
          <li>One account per person or restaurant. Don't share invite codes.</li>
        </ul>

        <h2>your data</h2>
        <ul>
          <li>What you upload stays yours.</li>
          <li>You allow Docket to store and process it to run the service, including sending it to Anthropic
            when you use an AI feature.</li>
          <li>Only upload data you have the right to use, and no personal details about other people that Docket
            doesn't need.</li>
        </ul>

        <h2>check the figures</h2>
        <ul>
          <li>Costs, margins and suggestions are worked out from the data you give. They are only as good as that
            data.</li>
          <li>AI reads menus, invoices and till exports, and estimates recipes. It can get things wrong, which is why
            every draft is shown to you before it's saved.</li>
          <li>Docket is not financial, tax, accounting or legal advice. Check any figure before acting on it.</li>
        </ul>

        <h2>fair use</h2>
        <p>
          Don't use Docket for anything unlawful, try to get into other accounts, overload or probe the service, or
          copy it by automated means. Accounts that do may be closed.
        </p>

        <h2>no guarantees</h2>
        <ul>
          <li>Docket is provided as it is, without any promise that it will always be available, error-free or
            suitable for a particular purpose.</li>
          <li>It may change, pause or close at any time. Where possible, account holders will get notice to take a
            copy of their data first.</li>
          <li>{OWNER} isn't liable for any loss of profit or business, or for decisions made using Docket. Nothing in
            these terms limits liability that the law doesn't allow to be limited.</li>
        </ul>

        <h2>the law</h2>
        <p>These terms are governed by the law of England and Wales.</p>

        <h2>contact</h2>
        <p><a href={`mailto:${CONTACT_EMAIL}`} className="link">{CONTACT_EMAIL}</a></p>
      </article>
    </PublicLayout>
  )
}

export default TermsPage
