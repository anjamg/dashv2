import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

type Call = {
  id: number
  datetime_tz_offset_incl: string | null
  team_name: string | null
  user_norm: string | null
  direction: string | null
  answered: boolean | number | null
  duration_total_sec: number | null
}

type CallsResponse = {
  data: Call[]
  page: number
  limit: number
  total: number
}

const pageSize = 50

function getLocalDate() {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

function formatDate(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export default function Calls() {
  const [team, setTeam] = useState('')
  const [user, setUser] = useState('')
  const [answered, setAnswered] = useState('')
  const [dateFrom, setDateFrom] = useState(getLocalDate)
  const [dateTo, setDateTo] = useState(getLocalDate)
  const [page, setPage] = useState(1)
  const params = {
    page,
    limit: pageSize,
    team: team.trim() || undefined,
    user: user.trim() || undefined,
    answered: answered === '' ? undefined : answered === 'yes',
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  }
  const calls = useQuery({
    queryKey: ['calls', params],
    queryFn: async () => (await api.get<CallsResponse>('/calls', { params })).data,
  })

  function updateFilter(setter: (value: string) => void, value: string) {
    setter(value)
    setPage(1)
  }

  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">ACTIVITÉ</p>
          <h1>Appels</h1>
          <p className="page-description">Explorez et filtrez les appels enregistrés.</p>
        </div>
        <span className="count-badge">{calls.data?.total ?? '—'} résultats</span>
      </header>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Filtres</h2>
            <p>Combinez les critères pour affiner les résultats.</p>
          </div>
          <button
            type="button"
            className="button button-subtle"
            onClick={() => {
              setTeam('')
              setUser('')
              setAnswered('')
              setDateFrom(getLocalDate())
              setDateTo(getLocalDate())
              setPage(1)
            }}
          >
            Réinitialiser
          </button>
        </div>
        <div className="filter-grid">
          <label className="field">
            <span>Équipe</span>
            <input value={team} onChange={(event) => updateFilter(setTeam, event.target.value)} placeholder="Toutes les équipes" />
          </label>
          <label className="field">
            <span>Utilisateur</span>
            <input value={user} onChange={(event) => updateFilter(setUser, event.target.value)} placeholder="Nom de l’utilisateur" />
          </label>
          <label className="field">
            <span>Réponse</span>
            <select value={answered} onChange={(event) => updateFilter(setAnswered, event.target.value)}>
              <option value="">Tous les appels</option>
              <option value="yes">Répondus</option>
              <option value="no">Manqués</option>
            </select>
          </label>
          <label className="field">
            <span>Du</span>
            <input type="date" value={dateFrom} onChange={(event) => updateFilter(setDateFrom, event.target.value)} />
          </label>
          <label className="field">
            <span>Au</span>
            <input type="date" value={dateTo} onChange={(event) => updateFilter(setDateTo, event.target.value)} />
          </label>
        </div>
      </section>

      <section className="panel table-panel">
        {calls.isPending ? (
          <p className="empty-state">Chargement des appels…</p>
        ) : calls.isError ? (
          <div className="empty-state error-state">
            <strong>Impossible de charger les appels.</strong>
            <span>Vérifiez la connexion à l’API, puis réessayez.</span>
            <button type="button" className="button button-subtle" onClick={() => calls.refetch()}>Réessayer</button>
          </div>
        ) : calls.data?.data.length ? (
          <>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr><th>Date</th><th>Équipe</th><th>Utilisateur</th><th>Direction</th><th>Statut</th><th>Durée</th></tr>
                </thead>
                <tbody>
                  {calls.data.data.map((call) => (
                    <tr key={call.id}>
                      <td>{formatDate(call.datetime_tz_offset_incl)}</td>
                      <td>{call.team_name || '—'}</td>
                      <td>{call.user_norm || '—'}</td>
                      <td>{call.direction || '—'}</td>
                      <td><span className={`status-pill ${call.answered ? 'status-positive' : 'status-muted'}`}>{call.answered ? 'Répondu' : 'Manqué'}</span></td>
                      <td>{call.duration_total_sec == null ? '—' : `${call.duration_total_sec} s`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>Page {page} sur {Math.max(1, Math.ceil((calls.data.total ?? 0) / pageSize))}</span>
              <div className="button-row">
                <button className="button button-subtle" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Précédent</button>
                <button className="button button-subtle" disabled={page * pageSize >= calls.data.total} onClick={() => setPage((current) => current + 1)}>Suivant</button>
              </div>
            </div>
          </>
        ) : (
          <p className="empty-state">Aucun appel ne correspond à ces filtres.</p>
        )}
      </section>
    </div>
  )
}
