import { useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, RefreshCw, Save } from 'lucide-react'
import { api } from '../api'

type Row = Record<string, string | number | null | undefined>

type N2Stats = Row & {
  total_appels: number
  pris: number
  sortants: number
  rebascules: number
  abandonnes: number
  hors_horaires: number
  taux_reponse: number
  nb_agents: number
  devis_ok: number
  devis_ko: number
}

function formatAgentName(value: string) {
  return value
    .replace(/^Niveau\s*2\s*-\s*/i, '')
    .replace(/^Vitalliance\s*-\s*/i, '')
    .trim() || '—'
}

type AgentRow = Row & {
  user: string
  total: number
  pris: number
  sortants: number
  rebascules?: number
  total_incall: number | null
  avg_incall?: number | null
}

type SviTeam = Row & {
  equipe: string
  abandonnes: number
  rebascules: number
  pris: number
  sortants: number
  total_traites: number
  effectifs: number
  calls_effectif: number
  taux_decro: number
}

type SqAgent = Row & {
  user: string
  appeles: number
  appels_entrants: number
  nb_client: number
  nb_adv: number
  nb_autres: number
  nb_ras: number
  nb_injoignable: number
  nb_questions_ok: number
  total_incall: number
  joignabilite: number
}

type Report = {
  date_from: string
  date_to: string
  note_date: string
  n2: { global: N2Stats; agents: AgentRow[] }
  recap: { by_team: SviTeam[]; by_agent: Record<string, AgentRow[]> }
  sq: {
    totaux: Row & {
      appeles: number
      appels_entrants: number
      injoignable: number
      joignabilite: number
      client_total: number
      adv_total: number
      client_inj: number
      client_decro: number
      client_entrants: number
      adv_inj: number
      adv_decro: number
      adv_entrants: number
      questions_ok: number
      bilan_positif: number
      bilan_mitige: number
      bilan_negatif: number
      sm_client_positif: number
      sm_client_mitige: number
      sm_client_negatif: number
      sm_client_inj2: number
      qs_client_positif: number
      qs_client_mitige: number
      qs_client_negatif: number
      qs_client_inj2: number
      sm_adv_positif: number
      sm_adv_mitige: number
      sm_adv_negatif: number
      sm_adv_inj2: number
      a_rappeler: number
      interrompu: number
      prime_participation: number
    }
    agents: SqAgent[]
  }
  comments: {
    n2: { lines: string[]; tag_lines: string[]; potential_calls: Row[] }
    svi: { lines: string[] }
  }
  absences: Array<Row & { user_id: number; agent_name: string; code: string; type_name: string }>
  organization: Record<string, string[]>
  organization_note: string
}

type TableColumn<T> = {
  key: keyof T
  label: string
  render?: (row: T) => ReactNode
}

const numberFormat = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 })

function getLocalDate() {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 10)
}

function formatNumber(value: unknown) {
  return value == null ? '—' : numberFormat.format(Number(value))
}

function formatPercent(value: number) {
  return new Intl.NumberFormat('fr-FR', { style: 'percent', maximumFractionDigits: 1 }).format(value || 0)
}

function formatDuration(value: number | null | undefined) {
  if (!value) return '—'
  const minutes = Math.floor(value / 60)
  const seconds = value % 60
  return minutes ? `${minutes} min ${String(seconds).padStart(2, '0')} s` : `${seconds} s`
}

function DataTable<T extends object>({ rows, columns, emptyText = 'Aucune donnée.' }: {
  rows: T[]
  columns: TableColumn<T>[]
  emptyText?: string
}) {
  if (!rows.length) return <p className="empty-state">{emptyText}</p>
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead><tr>{columns.map(({ key, label }) => <th key={String(key)}>{label}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={String((row as { id?: string | number }).id ?? index)}>
              {columns.map(({ key, render }) => (
                <td key={String(key)}>{render ? render(row) : String(row[key] ?? '—')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function KpiCards({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return (
    <div className="kpi-grid">
      {items.map(({ label, value }, index) => (
        <article className="kpi-card" key={label}>
          <span className={`kpi-mark kpi-mark-${index % 4}`} />
          <p>{label}</p><strong>{value}</strong>
        </article>
      ))}
    </div>
  )
}

function SectionHeading({ title, description }: { title: string; description?: string }) {
  return <div className="panel-heading"><div><h2>{title}</h2>{description && <p>{description}</p>}</div></div>
}

export default function Meteo() {
  const queryClient = useQueryClient()
  const today = getLocalDate()
  const [dateFrom, setDateFrom] = useState(today)
  const [dateTo, setDateTo] = useState(today)
  const [period, setPeriod] = useState<{ date_from: string; date_to: string } | null>(null)
  const [organizationText, setOrganizationText] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState('')
  const report = useQuery({
    queryKey: ['meteo-report', period],
    queryFn: async () => (await api.get<Report>('/meteo/report', { params: period })).data,
    enabled: period !== null,
  })
  const exportExcel = useMutation({
    mutationFn: async () => {
      if (!period) throw new Error('Choisissez une période avant de télécharger le rapport.')
      return api.get('/meteo/export', { params: period, responseType: 'blob' })
    },
    onSuccess: (response) => {
      if (!period) return
      const url = URL.createObjectURL(response.data)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `meteo_${period.date_from}_${period.date_to}.xlsx`
      anchor.click()
      URL.revokeObjectURL(url)
    },
  })
  const effectif = useQuery({
    queryKey: ['effectif', period?.date_to],
    queryFn: async () => (await api.get<Row[]>('/dashboard/effectif', { params: { date: period?.date_to } })).data,
    enabled: period !== null,
  })
  const saveNote = useMutation({
    mutationFn: async () => {
      if (!report.data) throw new Error('Le rapport est indisponible.')
      return api.post('/meteo/organization-note', {
        report_date: report.data.note_date,
        organization_text: organizationText ?? report.data.organization_note,
      })
    },
    onSuccess: async () => {
      setSaveMessage('Note d’organisation enregistrée.')
      await queryClient.invalidateQueries({ queryKey: ['meteo-report', period] })
    },
  })
  const reportData = report.data
  const n2 = reportData?.n2.global
  const sq = reportData?.sq.totaux
  const effectifColumns = effectif.data?.[0] ? Object.keys(effectif.data[0]) as Array<keyof Row> : []

  function calculate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaveMessage('')
    setOrganizationText(null)
    setPeriod({ date_from: dateFrom, date_to: dateTo })
  }

  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">REPORTING QUOTIDIEN</p>
          <h1>Météo du jour</h1>
          <p className="page-description">TCD DEB-N2 · RECAP SVI · STATS SQ</p>
        </div>
        <form className="meteo-controls" onSubmit={calculate}>
          <label className="field"><span>Du</span><input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} required /></label>
          <label className="field"><span>Au</span><input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} required min={dateFrom} /></label>
          <button className="button button-primary" type="submit"><RefreshCw size={15} /> Calculer</button>
          {reportData && <button className="button button-subtle" type="button" onClick={() => exportExcel.mutate()} disabled={exportExcel.isPending}><Download size={15} />{exportExcel.isPending ? 'Export…' : 'Export Excel'}</button>}
        </form>
      </header>

      {report.isError && <div className="notice notice-error">Impossible de générer le rapport Météo. Vérifiez la connexion à l’API et la disponibilité des vues et tables source.</div>}
      {saveNote.isError && <div className="notice notice-error">La note n’a pas pu être enregistrée. Réessayez.</div>}
      {exportExcel.isError && <div className="notice notice-error">L’export Excel n’a pas pu être généré.</div>}
      {saveMessage && <div className="notice notice-success">{saveMessage}</div>}
      {report.isPending && period && <p className="empty-state">Calcul du rapport…</p>}
      {!period && <section className="panel"><p className="empty-state">Choisissez une période et cliquez sur « Calculer » pour générer les sections du rapport.</p></section>}

      {reportData && (
        <>
          <section className="panel">
            <SectionHeading title="RECAP DEB-N2" description="Synthèse et détail des appels de l’équipe N2" />
            {n2 && <KpiCards items={[
              { label: 'Total appels', value: formatNumber(n2.total_appels) },
              { label: 'Pris', value: formatNumber(n2.pris) },
              { label: 'Sortants', value: formatNumber(n2.sortants) },
              { label: 'Rebasculés', value: formatNumber(n2.rebascules) },
              { label: 'Abandonnés', value: formatNumber(n2.abandonnes) },
              { label: 'Taux réponse', value: `${numberFormat.format(n2.taux_reponse)} %` },
              { label: 'Hors horaires', value: formatNumber(n2.hors_horaires) },
              { label: 'Agents', value: formatNumber(n2.nb_agents) },
              { label: 'Devis OK', value: formatNumber(n2.devis_ok) },
              { label: 'Devis KO', value: formatNumber(n2.devis_ko) },
            ]} />}
            <div className="report-table-block">
              <h3>Détail par agent N2</h3>
              <DataTable rows={reportData.n2.agents} columns={[
                { key: 'user', label: 'Agent', render: (row) => formatAgentName(row.user) },
                { key: 'total', label: 'Total', render: (row) => formatNumber(row.total) },
                { key: 'pris', label: 'Pris', render: (row) => formatNumber(row.pris) },
                { key: 'sortants', label: 'Sortants', render: (row) => formatNumber(row.sortants) },
                { key: 'rebascules', label: 'Rebasculés', render: (row) => formatNumber(row.rebascules) },
                { key: 'total_incall', label: 'Durée totale appel', render: (row) => formatDuration(row.total_incall) },
                { key: 'avg_incall', label: 'Durée moyenne in-call', render: (row) => formatDuration(row.avg_incall) },
              ]} />
            </div>
          </section>

          <section className="panel">
            <SectionHeading title="Commentaires automatiques" description="Commentaires quotidiens générés à partir des données N2 et SVI" />
            <div className="report-table-block">
              <h3>New N2</h3>
              <ul className="report-list">{reportData.comments.n2.lines.map((line) => <li key={line}>{line}</li>)}{reportData.comments.n2.tag_lines.map((line) => <li key={line}>{line}</li>)}</ul>
              <h3>SVI1 & 2 et SVI3 & HP</h3>
              <ul className="report-list">{reportData.comments.svi.lines.map((line) => <li key={line}>{line}</li>)}</ul>
            </div>
            <details className="report-details">
              <summary>Appels N2 qui auraient pu être pris ({reportData.comments.n2.potential_calls.length})</summary>
              <DataTable rows={reportData.comments.n2.potential_calls} emptyText="Aucun appel N2 concerné sur la période." columns={[
                { key: 'datetime', label: 'Date / heure' },
                { key: 'line', label: 'Ligne' },
                { key: 'customer_number', label: 'N° client' },
                { key: 'missed_call_reason', label: 'Motif' },
                { key: 'agents_present', label: 'Agents disponibles', render: (row) => `${Number(row.agents_present ?? 0) - Number(row.agents_busy ?? 0)} / ${row.agents_present ?? 0}` },
              ]} />
            </details>
          </section>

          <section className="panel">
            <SectionHeading title="RECAP SVI" description="DEB + CDN · volumes, taux de décroché et effectifs" />
            <DataTable rows={reportData.recap.by_team} columns={[
              { key: 'equipe', label: 'Équipe' },
              { key: 'abandonnes', label: 'Abandonnés', render: (row) => formatNumber(row.abandonnes) },
              { key: 'rebascules', label: 'Rebasculés', render: (row) => formatNumber(row.rebascules) },
              { key: 'pris', label: 'Pris', render: (row) => formatNumber(row.pris) },
              { key: 'sortants', label: 'Sortants', render: (row) => formatNumber(row.sortants) },
              { key: 'total_traites', label: 'Total traités', render: (row) => formatNumber(row.total_traites) },
              { key: 'effectifs', label: 'ETP', render: (row) => formatNumber(row.effectifs) },
              { key: 'calls_effectif', label: 'Calls/agent', render: (row) => formatNumber(row.calls_effectif) },
              { key: 'taux_decro', label: 'Taux décro', render: (row) => formatPercent(row.taux_decro) },
            ]} />
            {Object.entries(reportData.recap.by_agent).map(([label, agents]) => {
              const totals: AgentRow = {
                user: 'Total général',
                total: agents.reduce((sum, row) => sum + Number(row.total || 0), 0),
                pris: agents.reduce((sum, row) => sum + Number(row.pris || 0), 0),
                sortants: agents.reduce((sum, row) => sum + Number(row.sortants || 0), 0),
                total_incall: agents.reduce((sum, row) => sum + Number(row.total_incall || 0), 0),
              }
              return (
                <div className="report-table-block" key={label}>
                  <h3>Conseillers — {label}</h3>
                  <DataTable rows={agents.length ? [...agents, totals] : []} columns={[
                    { key: 'user', label: 'Agent', render: (row) => row.user === 'Total général' ? row.user : formatAgentName(row.user) },
                    { key: 'pris', label: 'Pris', render: (row) => formatNumber(row.pris) },
                    { key: 'sortants', label: 'Sortants', render: (row) => formatNumber(row.sortants) },
                    { key: 'total', label: 'Total', render: (row) => formatNumber(row.total) },
                    { key: 'total_incall', label: 'Temps total appel', render: (row) => formatDuration(row.total_incall) },
                  ]} />
                </div>
              )
            })}
          </section>

          <section className="panel">
            <SectionHeading title="STATS SQ" description="Suivi qualité · joignabilité, bilan et détail par conseiller" />
            {sq && <KpiCards items={[
              { label: 'Appels total', value: formatNumber(sq.client_total + sq.adv_total) },
              { label: 'Entrants', value: formatNumber(sq.appels_entrants) },
              { label: 'Injoignables', value: formatNumber(sq.injoignable) },
              { label: 'Joignabilité', value: formatPercent(sq.joignabilite) },
              { label: 'Questions OK', value: formatNumber(sq.questions_ok) },
              { label: 'À rappeler', value: formatNumber(sq.a_rappeler) },
              { label: 'Interrompus', value: formatNumber(sq.interrompu) },
              { label: 'Bilan positif', value: formatNumber(sq.bilan_positif) },
              { label: 'Bilan mitigé', value: formatNumber(sq.bilan_mitige) },
              { label: 'Bilan négatif', value: formatNumber(sq.bilan_negatif) },
              { label: 'Injoignable - clos', value: formatNumber(sq.sm_client_inj2 + sq.sm_adv_inj2 + sq.qs_client_inj2) },
              { label: 'Total - clos', value: formatNumber(sq.sm_client_inj2 + sq.sm_adv_inj2 + sq.qs_client_inj2 + sq.qs_client_positif + sq.bilan_positif + sq.bilan_mitige + sq.bilan_negatif) },
              { label: 'Prime participation', value: formatNumber(sq.prime_participation) },
            ]} />}
            <div className="report-table-block">
              <h3>Répartition CLIENT / ADV</h3>
              {sq && <DataTable rows={[
                { type: 'CLIENT', total: sq.client_total, entrants: sq.client_entrants, injoignable: sq.client_inj, rate: sq.client_total ? (sq.client_decro / sq.client_total) : 0 },
                { type: 'ADV', total: sq.adv_total, entrants: sq.adv_entrants, injoignable: sq.adv_inj, rate: sq.adv_total ? (sq.adv_decro / sq.adv_total) : 0 },
                { type: 'TOTAL', total: sq.client_total + sq.adv_total, entrants: sq.client_entrants + sq.adv_entrants, injoignable: sq.client_inj + sq.adv_inj, rate: sq.joignabilite },
              ]} columns={[
                { key: 'type', label: 'Type' },
                { key: 'total', label: 'Total appelés', render: (row) => formatNumber(row.total) },
                { key: 'entrants', label: 'Entrants', render: (row) => formatNumber(row.entrants) },
                { key: 'injoignable', label: 'Injoignables', render: (row) => formatNumber(row.injoignable) },
                { key: 'rate', label: '% Joignabilité', render: (row) => formatPercent(row.rate) },
              ]} />}
            </div>
            <div className="report-table-block">
              <h3>Bilan SQ</h3>
              {sq && <DataTable rows={[
                { type: 'CLIENT SM', positif: sq.sm_client_positif, mitige: sq.sm_client_mitige, negatif: sq.sm_client_negatif, injoignable: sq.sm_client_inj2 },
                { type: 'CLIENT QS', positif: sq.qs_client_positif, mitige: sq.qs_client_mitige, negatif: sq.qs_client_negatif, injoignable: sq.qs_client_inj2 },
                { type: 'ADV SM', positif: sq.sm_adv_positif, mitige: sq.sm_adv_mitige, negatif: sq.sm_adv_negatif, injoignable: sq.sm_adv_inj2 },
              ].map((row) => ({ ...row, total: row.positif + row.mitige + row.negatif + row.injoignable }))} columns={[
                { key: 'type', label: 'Type' },
                { key: 'positif', label: 'Positif', render: (row) => formatNumber(row.positif) },
                { key: 'mitige', label: 'Mitigé', render: (row) => formatNumber(row.mitige) },
                { key: 'negatif', label: 'Négatif', render: (row) => formatNumber(row.negatif) },
                { key: 'injoignable', label: 'Injoignable - Clos', render: (row) => formatNumber(row.injoignable) },
                { key: 'total', label: 'Total - Clos', render: (row) => formatNumber(row.total) },
              ]} />}
            </div>
            <div className="report-table-block">
              <h3>Joignabilité par conseiller SQ</h3>
              <DataTable rows={reportData.sq.agents} columns={[
                { key: 'user', label: 'Conseiller', render: (row) => formatAgentName(row.user) },
                { key: 'appeles', label: 'Appelés', render: (row) => formatNumber(row.appeles) },
                { key: 'appels_entrants', label: 'Entrants', render: (row) => formatNumber(row.appels_entrants) },
                { key: 'nb_client', label: 'Clients', render: (row) => formatNumber(row.nb_client) },
                { key: 'nb_adv', label: 'ADV', render: (row) => formatNumber(row.nb_adv) },
                { key: 'nb_autres', label: 'Autres', render: (row) => formatNumber(row.nb_autres) },
                { key: 'nb_ras', label: 'RAS', render: (row) => formatNumber(row.nb_ras) },
                { key: 'nb_injoignable', label: 'Injoignables', render: (row) => formatNumber(row.nb_injoignable) },
                { key: 'nb_questions_ok', label: 'Questions OK', render: (row) => formatNumber(row.nb_questions_ok) },
                { key: 'total_incall', label: 'Temps total appel', render: (row) => formatDuration(row.total_incall) },
                { key: 'joignabilite', label: '% Joignabilité', render: (row) => formatPercent(row.joignabilite) },
              ]} />
            </div>
          </section>

          <section className="panel">
            <SectionHeading title={`Absences / congés du ${new Date(`${reportData.note_date}T00:00:00`).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}`} description="Absences validées sur la journée suivant la fin de période" />
            {reportData.absences.length ? (
              <ul className="report-list">
                {reportData.absences.map((absence, index) => <li key={`${absence.user_id}-${index}`}>{absence.agent_name}{absence.code !== 'cp' && ` — ${absence.type_name}`}</li>)}
              </ul>
            ) : <p className="empty-state">Aucune absence validée sur cette date.</p>}
          </section>

          <section className="panel">
            <SectionHeading title={`Organisation pour le ${new Date(`${reportData.note_date}T00:00:00`).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}`} description="Équipes planifiées, hors collaborateurs absents" />
            {Object.keys(reportData.organization).length ? (
              <ul className="team-list">
                {Object.entries(reportData.organization).map(([team, members]) => <li key={team}><strong>{members.length} {team}</strong><span>{members.join(' + ')}</span></li>)}
              </ul>
            ) : <p className="empty-state">Aucun agent assigné à une équipe pour cette date.</p>}
            {reportData.organization_note && <div className="organization-note"><strong>Note complémentaire</strong><p>{reportData.organization_note}</p></div>}
            <form className="report-note-form" onSubmit={(event) => { event.preventDefault(); setSaveMessage(''); saveNote.mutate() }}>
              <label className="field"><span>Note complémentaire</span><textarea value={organizationText ?? reportData.organization_note} onChange={(event) => setOrganizationText(event.target.value)} maxLength={10000} placeholder="Organisation ou informations complémentaires…" /></label>
              <button className="button button-primary" type="submit" disabled={saveNote.isPending}><Save size={15} />{saveNote.isPending ? 'Enregistrement…' : 'Enregistrer la note'}</button>
            </form>
          </section>

          <section className="panel">
            <SectionHeading title="Effectifs par collaborateur" description="Données issues de la vue des effectifs du jour" />
            {effectif.isPending ? <p className="empty-state">Chargement des effectifs…</p> : effectif.isError ? <p className="empty-state error-state">Impossible de charger les effectifs. Vérifiez que la vue v_effectif_etp est disponible.</p> : (
              <DataTable rows={effectif.data ?? []} columns={effectifColumns.map((key) => ({
                key,
                label: String(key).replaceAll('_', ' '),
              }))} emptyText="Aucune donnée d’effectif pour cette date." />
            )}
          </section>
        </>
      )}
    </div>
  )
}
