import { Link, useParams } from 'react-router-dom'

function MeasurementPage() {
  const { setupId } = useParams<{ setupId: string }>()

  return (
    <div className="page">
      {setupId && (
        <Link to={`/setups/${setupId}`} className="back-link">
          ← Back to setup
        </Link>
      )}
      <h1>Measurement</h1>
      <p>Coming soon.</p>
    </div>
  )
}

export default MeasurementPage
