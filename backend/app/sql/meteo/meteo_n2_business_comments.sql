-- Commentaires metier N2 : appels entrants, rebascules, disponibilite agent
-- Params: :df_busy, :dt_busy, :df_agents, :dt_agents, :df_missed, :dt_missed,
--         :df_tags, :dt_tags, :df_rebasc, :dt_rebasc
--
-- Optimisation STEP 3 (2026-07) :
-- Les anciens EXISTS imbriqués (O(n²)) sont remplacés par des CTEs :
--   1. busy_intervals  : précalcule les intervalles d'appels actifs des agents N2
--   2. missed_base     : filtre les rebascules candidats (outbound, hors horaires, hors pause)
--   3. missed_enriched : classifie chaque rebasculé via LEFT JOIN sur busy_intervals
-- Les agrégats tags sont calculés séparément pour éviter un produit cartésien.
WITH
-- CTE 1 : intervalles d'appels en cours pour chaque agent N2 sur la période
busy_intervals AS (
    SELECT
        b.user,
        b.date_only,
        COALESCE(b.call_start_time, b.datetime_tz_offset_incl)         AS call_start,
        COALESCE(
            b.call_end_time,
            TIMESTAMPADD(
                SECOND,
                COALESCE(b.duration_in_call_sec, b.duration_total_sec, 0),
                COALESCE(b.call_start_time, b.datetime_tz_offset_incl)
            )
        )                                                               AS call_end
    FROM data b
    WHERE b.team_name = 'N2'
      AND b.user IS NOT NULL
      AND b.user != '[No associated user]'
      AND b.duration_in_call_sec > 0
      AND b.date_only >= :df_busy
      AND b.date_only <= :dt_busy
),
-- CTE 2 : agents N2 présents (au moins 1 enregistrement) par jour
agents_present AS (
    SELECT DISTINCT user, date_only
    FROM data
    WHERE team_name = 'N2'
      AND user IS NOT NULL
      AND user != '[No associated user]'
      AND date_only >= :df_agents
      AND date_only <= :dt_agents
),
-- CTE 3 : rebascules candidats (outbound N2, dans les horaires, hors pause déj. 12h-13h)
missed_base AS (
    SELECT
        d.id,
        d.datetime_tz_offset_incl,
        d.date_only,
        d.line,
        d.customer_number,
        d.missed_call_reason
    FROM data d
    WHERE d.team_name = 'N2'
      AND d.direction = 'outbound'
      AND d.user IS NULL
      AND d.out_of_hours = 0
      AND NOT (HOUR(d.datetime_tz_offset_incl) >= 12 AND HOUR(d.datetime_tz_offset_incl) < 13)
      AND d.date_only >= :df_missed
      AND d.date_only <= :dt_missed
),
-- CTE 4 : pour chaque rebasculé, compter agents présents vs agents occupés à cet instant
missed_enriched AS (
    SELECT
        m.id,
        m.datetime_tz_offset_incl,
        m.line,
        m.customer_number,
        m.missed_call_reason,
        COUNT(DISTINCT ap.user)                          AS nb_agents_present,
        -- Un agent est "occupé" si son intervalle d'appel englobe le timestamp du raté
        SUM(CASE
            WHEN bi.user IS NOT NULL
             AND bi.call_start <= m.datetime_tz_offset_incl
             AND bi.call_end   >= m.datetime_tz_offset_incl
            THEN 1 ELSE 0
        END)                                             AS nb_agents_busy
    FROM missed_base m
    LEFT JOIN agents_present ap  ON ap.date_only = m.date_only
    LEFT JOIN busy_intervals  bi ON bi.user       = ap.user
                                 AND bi.date_only  = m.date_only
    GROUP BY m.id
),
-- CTE 5 : agrégats tags (sur tous les appels N2, pas seulement les ratés)
tag_stats AS (
    SELECT
        SUM(d.tags IS NOT NULL AND d.tags LIKE '%PROSPECT%OK%')                                        AS prospects_ok_tag,
        SUM(d.tags IS NOT NULL AND d.tags LIKE '%DEVIS OK%')                                           AS devis_ok,
        SUM(d.tags IS NOT NULL AND d.tags LIKE '%DEVIS KO%')                                           AS devis_ko,
        SUM(d.tags IS NOT NULL AND (LOWER(d.tags) LIKE '%tchat%' OR LOWER(d.tags) LIKE '%chat%'))      AS tchats,
        SUM(d.tags IS NOT NULL AND d.tags LIKE '%CDN%')                                                AS cdn,
        SUM(d.tags IS NOT NULL AND d.tags LIKE '%Harisoa%')                                            AS harisoa,
        SUM(d.tags IS NOT NULL AND d.tags LIKE '%TRANSFERT N1%')                                       AS transfert_n1,
        SUM(d.tags IS NOT NULL AND (d.tags LIKE '%DEB-N2%' OR d.tags LIKE '%DEB N2%'))                AS deb_n2,
        SUM(d.tags IS NOT NULL AND d.tags LIKE '%NON DEB%')                                            AS non_deb,
        SUM(d.tags IS NOT NULL AND d.tags LIKE '%AS%' AND LOWER(d.tags) LIKE '%rappel%')               AS as_rappel
    FROM data d
    WHERE d.team_name = 'N2'
      AND d.date_only >= :df_tags
      AND d.date_only <= :dt_tags
),
-- CTE 6 : résumé des rebascules (totaux, pause, auraient pu être pris, agent en appel)
rebasc_stats AS (
    SELECT
        SUM(d.direction = 'outbound' AND d.user IS NULL AND d.out_of_hours = 0)          AS rebascules,
        SUM(d.direction = 'outbound' AND d.user IS NULL AND d.out_of_hours = 0
            AND HOUR(d.datetime_tz_offset_incl) >= 12
            AND HOUR(d.datetime_tz_offset_incl) < 13)                                    AS rebascules_pause,
        SUM(d.direction = 'inbound')                                                      AS appels_entrants
    FROM data d
    WHERE d.team_name = 'N2'
      AND d.date_only >= :df_rebasc
      AND d.date_only <= :dt_rebasc
)
SELECT
    rs.appels_entrants,
    rs.rebascules,
    rs.rebascules_pause,
    -- Auraient pu être pris : agent présent ET au moins 1 agent libre à cet instant
    SUM(CASE WHEN me.nb_agents_present > 0
                  AND me.nb_agents_busy < me.nb_agents_present
             THEN 1 ELSE 0 END)                     AS rebascules_auraient_pu_etre_pris,
    -- Agent en appel : tous les agents présents étaient occupés
    SUM(CASE WHEN me.nb_agents_present > 0
                  AND me.nb_agents_busy >= me.nb_agents_present
             THEN 1 ELSE 0 END)                     AS rebascules_agent_en_appel,
    ts.prospects_ok_tag,
    ts.devis_ok,
    ts.devis_ko,
    ts.tchats,
    ts.cdn,
    ts.harisoa,
    ts.transfert_n1,
    ts.deb_n2,
    ts.non_deb,
    ts.as_rappel
    , JSON_ARRAYAGG(
        CASE WHEN me.nb_agents_present > 0
                   AND me.nb_agents_busy < me.nb_agents_present
             THEN JSON_OBJECT(
                 'id', me.id,
                 'datetime', DATE_FORMAT(me.datetime_tz_offset_incl, '%Y-%m-%d %H:%i:%s'),
                 'line', COALESCE(me.line, ''),
                 'customer_number', COALESCE(me.customer_number, ''),
                 'missed_call_reason', COALESCE(me.missed_call_reason, ''),
                 'agents_present', me.nb_agents_present,
                 'agents_busy', me.nb_agents_busy
             )
             ELSE NULL
        END
      ) AS potential_calls
FROM missed_enriched me
CROSS JOIN rebasc_stats rs
CROSS JOIN tag_stats    ts
