-- STATS SQ : joignabilité par conseiller
-- Params: :df, :dt
SELECT
    d.user,
    COUNT(*)                                                    AS appeles,
    SUM(d.direction = 'inbound')                                AS appels_entrants,
    SUM(d.answered = 1)                                         AS decroches,
    SUM(d.tags LIKE '%2.CLIENT%')                               AS nb_client,
    SUM(d.tags LIKE '%2.ADV%')                                  AS nb_adv,
    SUM(d.tags LIKE '%Injoignable%')                            AS nb_injoignable,
    SUM(d.tags LIKE '%QUESTIONS OK%')                           AS nb_questions_ok,
    SUM(d.tags LIKE '%0. AUTRE%')                               AS nb_autres,
    SUM(d.tags LIKE '%3.RAS%')                                  AS nb_ras,
    COALESCE(SUM(d.duration_in_call_sec), 0)                     AS total_incall,
    ROUND(((SUM(d.tags LIKE '%2.CLIENT%')+SUM(d.tags LIKE '%2.ADV%'))-SUM(d.tags LIKE '%Injoignable%') ) * 1.0 / NULLIF(COUNT(*), 0), 4)   AS joignabilite /* joignabilite= (Total appels -Inj)/ total appels */
FROM data d
WHERE d.team_name = 'Suivi Qualité'
  -- AND d.direction = 'outbound' -- on considère tous les appels, pas seulement les sortants
  AND d.user IS NOT NULL
  AND d.user != '[No associated user]'
  AND d.date_only >= :df
  AND d.date_only <= :dt
GROUP BY d.user
ORDER BY appeles DESC
