import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

type LeaveRequest = {
  id: number
  username: string
  leave_name: string
  start_date: string | null
  end_date: string | null
  duration_days: number | string | null
  status: string | null
  reason: string | null
}

const statusLabels: Record<string, string> = {
  pending: 'En attente',
  approved: 'Approuvée',
  rejected: 'Refusée',
}

export default function Leaves() {
  const [status, setStatus] = useState('')
  const requests = useQuery({
    queryKey: ['leave-requests', status],
    queryFn: async () => (await api.get<LeaveRequest[]>('/leaves/requests', { params: { status: status || undefined } })).data,
  })

  return (
    <div className="page-stack">
      <header className="page-heading">
        <div><p className="eyebrow">GESTION DES ABSENCES</p><h1>Congés</h1><p className="page-description">Consultez les demandes de congés enregistrées.</p></div>
        <label className="field"><span>Statut</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Tous les statuts</option><option value="pending">En attente</option><option value="approved">Approuvées</option><option value="rejected">Refusées</option></select></label>
      </header>
      <section className="panel table-panel">
        {requests.isPending ? <p className="empty-state">Chargement des demandes…</p> : requests.isError ? (
          <div className="empty-state error-state"><strong>Impossible de charger les demandes.</strong><span>Vérifiez la connexion à l’API.</span><button className="button button-subtle" onClick={() => requests.refetch()}>Réessayer</button></div>
        ) : requests.data?.length ? (
          <div className="table-scroll"><table className="data-table"><thead><tr><th>Collaborateur</th><th>Type</th><th>Du</th><th>Au</th><th>Durée</th><th>Statut</th><th>Motif</th></tr></thead><tbody>
            {requests.data.map((request) => <tr key={request.id}><td>{request.username}</td><td>{request.leave_name}</td><td>{request.start_date || '—'}</td><td>{request.end_date || '—'}</td><td>{request.duration_days == null ? '—' : `${request.duration_days} j`}</td><td><span className="status-pill status-muted">{statusLabels[request.status || ''] || request.status || 'Inconnu'}</span></td><td>{request.reason || '—'}</td></tr>)}
          </tbody></table></div>
        ) : <p className="empty-state">Aucune demande pour ce statut.</p>}
      </section>
    </div>
  )
}
