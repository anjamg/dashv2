import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { useState } from 'react'

type Kpis = {
  total_calls: number | string | null
  answered: number | string | null
  missed: number | string | null
  avg_duration: number | string | null
  avg_wait: number | string | null
}

type TeamStats = {
  team_name: string
  calls: number
  answered: number
  avg_dur: number | null
}

type CallResultStats = {
  call_date: string
  team_name: string
  answered: number
  abandoned: number
  missed: number
  outside_hours: number
}

const numberFormat = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 })

function getLocalDate() {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

function formatDay(value: string) {
  const [, month, day] = value.split('-')
  return `${day}/${month}`
}

export default function Dashboard() {
  const [dateFrom, setDateFrom] = useState(getLocalDate)
  const [dateTo, setDateTo] = useState(getLocalDate)
  const filters = { date_from: dateFrom || undefined, date_to: dateTo || undefined }
  const kpis = useQuery({
    queryKey: ['dashboard-kpis', filters],
    queryFn: async () => (await api.get<Kpis>('/dashboard/kpis', { params: filters })).data,
  })
  const teams = useQuery({
    queryKey: ['dashboard-by-team', filters],
    queryFn: async () => (await api.get<TeamStats[]>('/dashboard/by-team', { params: filters })).data,
  })
  const results = useQuery({
    queryKey: ['dashboard-by-result', filters],
    queryFn: async () => (await api.get<CallResultStats[]>('/dashboard/by-result', { params: filters })).data,
  })
  const cards = [
    { label: 'Appels au total', value: kpis.data?.total_calls },
    { label: 'Appels répondus', value: kpis.data?.answered },
    { label: 'Appels manqués', value: kpis.data?.missed },
    { label: 'Attente moyenne', value: kpis.data?.avg_wait == null ? null : `${numberFormat.format(Number(kpis.data.avg_wait))} s` },
  ]

  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">VUE D’ENSEMBLE</p>
          <h1>Bonjour 👋</h1>
          <p className="page-description">Suivez l’activité des équipes sur la période choisie.</p>
        </div>
        <div className="date-range">
          <label className="field"><span>Du</span><input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
          <label className="field"><span>Au</span><input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
        </div>
      </header>

      {kpis.isError && <div className="notice notice-error">Les indicateurs n’ont pas pu être chargés. Vérifiez la connexion à l’API.</div>}
      <section className="kpi-grid">
        {cards.map((card, index) => (
          <article className="kpi-card" key={card.label}>
            <span className={`kpi-mark kpi-mark-${index}`} />
            <p>{card.label}</p>
            <strong>{card.value == null ? (kpis.isPending ? '…' : '—') : typeof card.value === 'number' || typeof card.value === 'string' && !card.value.includes('s') ? numberFormat.format(Number(card.value)) : card.value}</strong>
          </article>
        ))}
      </section>

      <section className="panel chart-panel">
        <div className="panel-heading">
          <div><h2>Résultats des appels</h2><p>Répartition quotidienne par équipe et par résultat</p></div>
        </div>
        {results.isPending ? <p className="empty-state">Chargement des données…</p> : results.isError ? (
          <p className="empty-state error-state">Impossible de charger les résultats des appels.</p>
        ) : results.data?.length ? (
          <div className="chart-area" style={{ overflowX: 'auto' }}>
            <div style={{ minWidth: `${Math.max(640, results.data.length * 90)}px`, height: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={results.data.map((row) => ({
                    ...row,
                    label: `${formatDay(row.call_date)} · ${row.team_name}`,
                  }))}
                  margin={{ top: 8, right: 12, left: -16, bottom: 32 }}
                >
                <CartesianGrid stroke="#edf0f5" vertical={false} />
                <XAxis dataKey="label" interval={0} angle={-35} textAnchor="end" height={72} axisLine={false} tickLine={false} tick={{ fill: '#778196', fontSize: 11 }} />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: '#778196', fontSize: 12 }} />
                <Tooltip cursor={{ fill: '#f1f5f9' }} />
                <Bar dataKey="answered" name="Répondus" stackId="results" fill="#159473" maxBarSize={52} />
                <Bar dataKey="abandoned" name="Abandonnés" stackId="results" fill="#c39316" maxBarSize={52} />
                <Bar dataKey="missed" name="Manqués" stackId="results" fill="#b63f4c" maxBarSize={52} />
                <Bar dataKey="outside_hours" name="Hors horaires" stackId="results" fill="#68758b" radius={[4, 4, 0, 0]} maxBarSize={52} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : <p className="empty-state">Aucun appel disponible pour cette période.</p>}
      </section>

      <section className="panel chart-panel">
        <div className="panel-heading">
          <div><h2>Activité par équipe</h2><p>Volume d’appels pour la période sélectionnée</p></div>
        </div>
        {teams.isPending ? <p className="empty-state">Chargement des données…</p> : teams.isError ? (
          <p className="empty-state error-state">Impossible de charger les statistiques par équipe.</p>
        ) : teams.data?.length ? (
          <div className="chart-area">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={teams.data} margin={{ top: 8, right: 12, left: -16, bottom: 4 }}>
                <CartesianGrid stroke="#edf0f5" vertical={false} />
                <XAxis dataKey="team_name" axisLine={false} tickLine={false} tick={{ fill: '#778196', fontSize: 12 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#778196', fontSize: 12 }} />
                <Tooltip cursor={{ fill: '#f1f5f9' }} />
                <Bar dataKey="calls" name="Appels" fill="#5465e8" radius={[6, 6, 0, 0]} maxBarSize={48} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <p className="empty-state">Aucune donnée disponible pour cette période.</p>}
      </section>
    </div>
  )
}
