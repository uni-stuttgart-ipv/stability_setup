import './ChartPlaceholder.css'

interface ChartPlaceholderProps {
  title: string
}

function ChartPlaceholder({ title }: ChartPlaceholderProps) {
  return (
    <div className="chart-placeholder">
      <h4>{title}</h4>
      <div className="chart-placeholder__box">Chart coming soon</div>
    </div>
  )
}

export default ChartPlaceholder
