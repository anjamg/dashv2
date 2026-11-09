import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'

type ImportRecord = {
  id: number
  filename: string | null
  imported_at: string | null
  rows_inserted: number
  rows_skipped: number
  status: string | null
}

type ImportResult = {
  inserted: number
  updated: number
  skipped: number
  without_user: number
  without_call_id: number
  stats_synced: number
  filename: string
}

export default function Imports() {
  const [file, setFile] = useState<File | null>(null)
  const queryClient = useQueryClient()
  const history = useQuery({
    queryKey: ['import-history'],
    queryFn: async () => (await api.get<ImportRecord[]>('/imports/history')).data,
  })
  const upload = useMutation({
    mutationFn: async (selectedFile: File) => {
      const body = new FormData()
      body.append('file', selectedFile)
      return (await api.post<ImportResult>('/imports/aircall', body)).data
    },
    onSuccess: async () => {
      setFile(null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['import-history'] }),
        queryClient.invalidateQueries({ queryKey: ['calls'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-kpis'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-by-team'] }),
      ])
    },
  })
  const uploadError = upload.error as { response?: { data?: { detail?: string } } } | null

  return (
    <div className="page-stack">
      <header className="page-heading"><div><p className="eyebrow">DONNÉES</p><h1>Imports</h1><p className="page-description">Importez un export Aircall au format Excel et suivez l’historique.</p></div></header>
      <section className="panel">
        <div className="panel-heading"><div><h2>Importer des appels Aircall</h2><p>Fichier .xlsx, limité à 15 Mo. Les lignes sans données sont ignorées; les appels sans agent restent importés sans attribution.</p></div></div>
        <div className="filter-grid import-controls">
          <label className="field"><span>Fichier Excel</span><input type="file" accept=".xlsx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>
          <div className="import-action"><button className="button button-primary" disabled={!file || upload.isPending} onClick={() => file && upload.mutate(file)}>{upload.isPending ? 'Import en cours…' : 'Importer le fichier'}</button>{file && <span className="file-name">{file.name}</span>}</div>
        </div>
        {upload.isError && <p className="form-feedback form-feedback-error">{uploadError?.response?.data?.detail || 'L’import a échoué. Vérifiez le fichier et réessayez.'}</p>}
        {upload.isSuccess && <div className="form-feedback form-feedback-success"><p>{upload.data.inserted} nouveaux appels, {upload.data.updated} mis à jour, {upload.data.skipped} lignes ignorées.</p><p>{upload.data.stats_synced} lignes statistiques synchronisées.</p>{upload.data.without_user > 0 && <p>{upload.data.without_user} appels n’avaient pas d’agent associé.</p>}{upload.data.without_call_id > 0 && <p>{upload.data.without_call_id} appels n’avaient pas de call ID et ne pourront pas être dédupliqués.</p>}</div>}
      </section>
      <section className="panel table-panel">
        <div className="panel-heading"><div><h2>Historique des imports</h2><p>Les 100 derniers imports</p></div><button className="button button-subtle" onClick={() => history.refetch()}>Actualiser</button></div>
        {history.isPending ? <p className="empty-state">Chargement de l’historique…</p> : history.isError ? <div className="empty-state error-state"><strong>Impossible de charger l’historique.</strong><span>Vérifiez la connexion à l’API.</span><button className="button button-subtle" onClick={() => history.refetch()}>Réessayer</button></div> : history.data?.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Fichier</th><th>Date d’import</th><th>Lignes traitées</th><th>Ignorées</th><th>Statut</th></tr></thead><tbody>{history.data.map((record) => <tr key={record.id}><td>{record.filename || '—'}</td><td>{record.imported_at ? new Date(record.imported_at).toLocaleString() : '—'}</td><td>{record.rows_inserted}</td><td>{record.rows_skipped}</td><td>{record.status || '—'}</td></tr>)}</tbody></table></div> : <p className="empty-state">Aucun import enregistré.</p>}
      </section>
    </div>
  )
}
