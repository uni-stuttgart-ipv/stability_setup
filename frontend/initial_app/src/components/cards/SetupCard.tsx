import type { Setup } from '../../types'
import { statusDotClass } from '../../utils/statusColors'

interface SetupCardProps {
  setup: Setup
  onClick: () => void
}

function SetupCard({ setup, onClick }: SetupCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex cursor-pointer flex-col gap-[0.4rem] rounded-[10px] border border-border bg-surface px-[1.1rem] py-4 text-left transition-[border-color,transform] duration-150 ease-in-out hover:-translate-y-0.5 hover:border-accent"
    >
      <div className="flex items-center justify-between">
        <h3 className="m-0 text-[1.05rem]">{setup.name}</h3>
        <span className={`h-[10px] w-[10px] shrink-0 rounded-full ${statusDotClass(setup.solarSimulatorStatus)}`} />
      </div>
      <p className="m-0 text-[0.85rem] text-text-muted">{setup.location}</p>
      <p className={`m-0 text-[0.85rem] ${setup.currentUser ? 'font-medium' : 'font-normal text-text-muted'}`}>
        {setup.currentUser ? `In use by ${setup.currentUser}` : 'Available'}
      </p>
    </button>
  )
}

export default SetupCard
