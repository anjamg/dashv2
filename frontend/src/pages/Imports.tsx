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

type ImportResult = { inserted: number; skipped: number; filename: string }

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
      await queryClient.invalidateQueries({ queryKey: ['import-history'] })
    },
  })
  const uploadError = upload.error as { response?: { data?: { detail?: string } } } | null

  return (
    <div className="page-stack">
      <header className="page-heading"><div><p className="eyebrow">DONNÉES</p><h1>Imports</h1><p className="page-description">Importez un export Aircall au format Excel et suivez l’historique.</p></div></header>
      <section className="panel">
        <div className="panel-heading"><div><h2>Importer des appels Aircall</h2><p>Fichier .xlsx, limité à 15 Mo. Les lignes sans données sont ignorées.</p></div></div>
        <div className="filter-grid import-controls">
          <label className="field"><span>Fichier Excel</span><input type="file" accept=".xlsx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>
          <div className="import-action"><button className="button button-primary" disabled={!file || upload.isPending} onClick={() => file && upload.mutate(file)}>{upload.isPending ? 'Import en cours…' : 'Importer le fichier'}</button>{file && <span className="file-name">{file.name}</span>}</div>
        </div>
        {upload.isError && <p className="form-feedback form-feedback-error">{uploadError?.response?.data?.detail || 'L’import a échoué. Vérifiez le fichier et réessayez.'}</p>}
        {upload.isSuccess && <p className="form-feedback form-feedback-success">{upload.data.inserted} appels importés, {upload.data.skipped} lignes ignorées.</p>}
      </section>
      <section className="panel table-panel">
        <div className="panel-heading"><div><h2>Historique des imports</h2><p>Les 100 derniers imports</p></div><button className="button button-subtle" onClick={() => history.refetch()}>Actualiser</button></div>
        {history.isPending ? <p className="empty-state">Chargement de l’historique…</p> : history.isError ? <div className="empty-state error-state"><strong>Impossible de charger l’historique.</strong><span>Vérifiez la connexion à l’API.</span><button className="button button-subtle" onClick={() => history.refetch()}>Réessayer</button></div> : history.data?.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Fichier</th><th>Date d’import</th><th>Importées</th><th>Ignorées</th><th>Statut</th></tr></thead><tbody>{history.data.map((record) => <tr key={record.id}><td>{record.filename || '—'}</td><td>{record.imported_at ? new Date(record.imported_at).toLocaleString() : '—'}</td><td>{record.rows_inserted}</td><td>{record.rows_skipped}</td><td>{record.status || '—'}</td></tr>)}</tbody></table></div> : <p className="empty-state">Aucun import enregistré.</p>}
      </section>
    </div>
  )
}
