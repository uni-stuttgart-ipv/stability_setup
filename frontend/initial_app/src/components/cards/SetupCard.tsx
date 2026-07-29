import type { Setup } from '../../types'
import './SetupCard.css'

interface SetupCardProps {
  setup: Setup
  onClick: () => void
}

function SetupCard({ setup, onClick }: SetupCardProps) {
  return (
    <button type="button" className="setup-card" onClick={onClick}>
      <div className="setup-card__header">
        <h3>{setup.name}</h3>
        <span className={`status-dot status-dot--${setup.solarSimulatorStatus}`} />
      </div>
      <p className="setup-card__location">{setup.location}</p>
      <p className={`setup-card__user ${setup.currentUser ? '' : 'setup-card__user--free'}`}>
        {setup.currentUser ? `In use by ${setup.currentUser}` : 'Available'}
      </p>
    </button>
  )
}

export default SetupCard
