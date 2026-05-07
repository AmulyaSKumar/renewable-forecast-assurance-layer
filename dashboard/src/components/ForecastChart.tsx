import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type ChartRow = {
  timestamp: string
  forecast_p10_mw: number
  forecast_p50_mw: number
  forecast_p90_mw: number
  actual_mw?: number
}

function formatLabel(value: unknown) {
  return new Date(String(value)).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function ForecastChart({ data, title }: { data: ChartRow[]; title: string }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <h3>{title}</h3>
          <p>P10 / P50 / P90 confidence band for the next 24 hours.</p>
        </div>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={data}>
            <CartesianGrid stroke="rgba(148,163,184,0.16)" vertical={false} />
            <XAxis
              dataKey="timestamp"
              tickFormatter={(value) => new Date(value).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
            />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <Tooltip labelFormatter={formatLabel} />
            <Area type="monotone" dataKey="forecast_p90_mw" stroke="#1d4ed8" fill="#1d4ed8" fillOpacity={0.08} />
            <Area type="monotone" dataKey="forecast_p10_mw" stroke="#1d4ed8" fill="#0f172a" fillOpacity={1} />
            <Line type="monotone" dataKey="forecast_p50_mw" stroke="#38bdf8" strokeWidth={2.6} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

export function ComparisonChart({ data, title }: { data: ChartRow[]; title: string }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <h3>{title}</h3>
          <p>Recent observed output against the forecast median.</p>
        </div>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data}>
            <CartesianGrid stroke="rgba(148,163,184,0.16)" vertical={false} />
            <XAxis
              dataKey="timestamp"
              tickFormatter={(value) => new Date(value).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
            />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <Tooltip labelFormatter={formatLabel} />
            <Line type="monotone" dataKey="forecast_p50_mw" stroke="#38bdf8" strokeWidth={2.5} dot={false} />
            <Line type="monotone" dataKey="actual_mw" stroke="#f59e0b" strokeWidth={2.1} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
