import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

interface BackLinkProps {
  to: string
  children: ReactNode
}

function BackLink({ to, children }: BackLinkProps) {
  return (
    <Link to={to} className="mb-3 inline-block text-[0.9rem] text-text-muted no-underline hover:text-accent">
      {children}
    </Link>
  )
}

export default BackLink
