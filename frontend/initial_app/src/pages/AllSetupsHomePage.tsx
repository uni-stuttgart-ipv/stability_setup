import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchSetups } from '../api/mockApi'
import SetupCard from '../components/cards/SetupCard'
import type { Setup } from '../types'
import './AllSetupsHomePage.css'

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
    <div className="page">
      <h1>All Setups</h1>
      {loading ? (
        <p>Loading setups…</p>
      ) : (
        <div className="setup-grid">
          {setups.map((setup) => (
            <SetupCard key={setup.id} setup={setup} onClick={() => navigate(`/setups/${setup.id}`)} />
          ))}
        </div>
      )}
    </div>
  )
}

export default AllSetupsHomePage
