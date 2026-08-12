import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchSetups } from '../api/mockApi'
import SetupCard from '../components/cards/SetupCard'
import Page from '../components/layout/Page'
import type { Setup } from '../types'

function AllSetupsHomePage() {
  const navigate = useNavigate()
  const [setups, setSetups] = useState<Setup[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchSetups().then((data) => {
      if (!cancelled) {
        setSetups(data)
        setLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <Page>
      <h1>All Setups</h1>
      {loading ? (
        <p>Loading setups…</p>
      ) : (
        <div className="mt-5 grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
          {setups.map((setup) => (
            <SetupCard key={setup.id} setup={setup} onClick={() => navigate(`/setups/${setup.id}`)} />
          ))}
        </div>
      )}
    </Page>
  )
}

export default AllSetupsHomePage
