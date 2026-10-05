import { useParams } from 'react-router-dom'
import BackLink from '../components/layout/BackLink'
import Page from '../components/layout/Page'

function MeasurementPage() {
  const { setupId } = useParams<{ setupId: string }>()

  return (
    <Page>
      {setupId && <BackLink to={`/setups/${setupId}`}>← Back to setup</BackLink>}
      <h1>Measurement</h1>
      <p>Coming soon.</p>
    </Page>
  )
}

export default MeasurementPage
