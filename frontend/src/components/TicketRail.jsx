import Stamp from './Stamp'
import { VERB } from '../actionText'
import { poundsRounded } from '../format'

// Recommended changes as order tickets hanging off a rail. Each ticket is a
// link to its dish. The tilts repeat in a fixed pattern (not random), so the
// rail looks the same on every visit.
const TILTS = [-2.2, 1.4, -0.8, 2, -1.4]
const STAMP_TILTS = [-4, 3, -2, 2, -3]

export function Ticket({ action, category, number, tilt = 0, stampTilt = -3 }) {
  return (
    <a href={`#/menu/${action.dish_id}`} className="ticket" style={{ '--tilt': `${tilt}deg` }}>
      <span className="ticket-clip" aria-hidden="true" />
      <span className="ticket-meta">
        <span>TKT {String(number).padStart(2, '0')}</span>
        {category && <span>{category}</span>}
      </span>
      <span className="ticket-name">{action.dish_name}</span>
      <Stamp quadrant={action.quadrant} tilt={stampTilt} />
      <span className="ticket-foot">
        <span>{VERB[action.quadrant]?.toLowerCase()}</span>
        <span className="ticket-impact">+{poundsRounded(action.impact_pounds)}</span>
      </span>
    </a>
  )
}

// `actions` come from the action list (already ranked); `categoryOf` maps a
// dish id to its category for the ticket's corner.
function TicketRail({ actions, categoryOf = () => null, start = 1 }) {
  return (
    <div>
      <div className="rail" />
      <div className="rail-tickets">
        {actions.map((action, i) => (
          <Ticket key={action.dish_id} action={action} category={categoryOf(action.dish_id)}
                  number={start + i} tilt={TILTS[i % TILTS.length]} stampTilt={STAMP_TILTS[(start + i) % STAMP_TILTS.length]} />
        ))}
      </div>
    </div>
  )
}

export default TicketRail
