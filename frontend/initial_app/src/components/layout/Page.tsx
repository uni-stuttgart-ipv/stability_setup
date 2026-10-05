import type { ReactNode } from 'react'

interface PageProps {
  children: ReactNode
}

function Page({ children }: PageProps) {
  return <div className="mx-auto max-w-[960px] px-6 pt-8 pb-16">{children}</div>
}

export default Page
