import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

type TimeEntry = {
  id: number
  agent: string
  team_name: string | null
  date: string
  hours: number | string
  project_name: string | null
  code: string | null
  note: string | null
}

const numberFormat = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 })

export default function TimeTracking() {
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [team, setTeam] = useState('')
  const params = { date_from: dateFrom || undefined, date_to: dateTo || undefined, team: team.trim() || undefined }
  const entries = useQuery({
    queryKey: ['time-entries', params],
    queryFn: async () => (await api.get<TimeEntry[]>('/time/entries', { params })).data,
  })
  const totalHours = entries.data?.reduce((total, entry) => total + Number(entry.hours || 0), 0) ?? 0

  return (
    <div className="page-stack">
      <header className="page-heading"><div><p className="eyebrow">SUIVI D’ACTIVITÉ</p><h1>Temps & ETP</h1><p className="page-description">Consultez les temps déclarés par collaborateur et projet.</p></div><span className="count-badge">{entries.data?.length ?? '—'} entrées · {numberFormat.format(totalHours)} h</span></header>
      <section className="panel"><div className="filter-grid">
        <label className="field"><span>Du</span><input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
        <label className="field"><span>Au</span><input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
        <label className="field"><span>Équipe</span><input value={team} onChange={(event) => setTeam(event.target.value)} placeholder="Toutes les équipes" /></label>
      </div></section>
      <section className="panel table-panel">
        {entries.isPending ? <p className="empty-state">Chargement des temps…</p> : entries.isError ? <div className="empty-state error-state"><strong>Impossible de charger les temps.</strong><span>Vérifiez la connexion à l’API.</span><button className="button button-subtle" onClick={() => entries.refetch()}>Réessayer</button></div> : entries.data?.length ? (
          <div className="table-scroll"><table className="data-table"><thead><tr><th>Date</th><th>Collaborateur</th><th>Équipe</th><th>Projet</th><th>Heures</th><th>Note</th></tr></thead><tbody>{entries.data.map((entry) => <tr key={entry.id}><td>{entry.date}</td><td>{entry.agent}</td><td>{entry.team_name || '—'}</td><td>{entry.project_name || entry.code || '—'}</td><td>{numberFormat.format(Number(entry.hours))} h</td><td>{entry.note || '—'}</td></tr>)}</tbody></table></div>
        ) : <p className="empty-state">Aucune entrée de temps pour ces critères.</p>}
      </section>
    </div>
  )
}
