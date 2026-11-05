import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

type Department = { id: number; code: string; nom: string }
type Tarif = Record<string, string | number | null> & { id: number; tranche_heures?: string; dept_code?: string; nom?: string }
const tarifTypes = [
  { value: 'standard', label: 'Prestataire standard' },
  { value: 'apa', label: 'APA' },
  { value: 'carsat', label: 'CARSAT' },
  { value: 'pch', label: 'PCH' },
]

export default function Tarifs() {
  const [type, setType] = useState('standard')
  const [departmentId, setDepartmentId] = useState('')
  const departments = useQuery({ queryKey: ['departments'], queryFn: async () => (await api.get<Department[]>('/tarifs/departements')).data })
  const tarifs = useQuery({
    queryKey: ['tarifs', type, departmentId],
    queryFn: async () => (await api.get<Tarif[]>(`/tarifs/prestataire/${type}`, { params: { departement_id: departmentId || undefined } })).data,
  })
  const headers = tarifs.data?.[0] ? Object.keys(tarifs.data[0]).filter((key) => key !== 'id' && key !== 'departement_id') : []
  const labels: Record<string, string> = { dept_code: 'Département', nom: 'Nom', tranche_heures: 'Tranche horaire', lun_sam_ttc: 'Lun.–sam. TTC', dim_feries_ttc: 'Dimanches & fériés TTC', mai_dec_ttc: 'Mai–déc. TTC', normal_ttc: 'Tarif normal TTC' }

  return (
    <div className="page-stack">
      <header className="page-heading"><div><p className="eyebrow">RÉFÉRENTIEL</p><h1>Tarifs</h1><p className="page-description">Consultez les grilles tarifaires par dispositif et département.</p></div></header>
      <section className="panel">
        <div className="filter-grid">
          <label className="field"><span>Grille tarifaire</span><select value={type} onChange={(event) => setType(event.target.value)}>{tarifTypes.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}</select></label>
          <label className="field"><span>Département</span><select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)}><option value="">Tous les départements</option>{departments.data?.map((department) => <option value={department.id} key={department.id}>{department.code} — {department.nom}</option>)}</select></label>
        </div>
      </section>
      {departments.isError && <div className="notice notice-error">Impossible de charger la liste des départements.</div>}
      <section className="panel table-panel">
        {tarifs.isPending ? <p className="empty-state">Chargement des tarifs…</p> : tarifs.isError ? (
          <div className="empty-state error-state"><strong>Impossible de charger cette grille.</strong><span>Vérifiez la connexion à l’API.</span><button className="button button-subtle" onClick={() => tarifs.refetch()}>Réessayer</button></div>
        ) : tarifs.data?.length ? <div className="table-scroll"><table className="data-table"><thead><tr>{headers.map((header) => <th key={header}>{labels[header] || header.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{tarifs.data.map((row) => <tr key={row.id}>{headers.map((header) => <td key={header}>{row[header] == null ? '—' : header.endsWith('_ttc') ? `${Number(row[header]).toFixed(2)} €` : row[header]}</td>)}</tr>)}</tbody></table></div> : <p className="empty-state">Aucun tarif pour ces critères.</p>}
      </section>
    </div>
  )
}
