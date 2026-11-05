-- STATS SQ : stats globales Suivi Qualité (sortants avec agent)
-- Params: :df, :dt
SELECT
    COUNT(*)                                                        AS appeles,
    SUM(d.direction = 'inbound')                                    AS appels_entrants,
    SUM(d.answered = 1)                                             AS decroches,
    SUM(d.tags IS NOT NULL AND d.tags LIKE '%2.CLIENT%')            AS nb_client,
    SUM(d.tags IS NOT NULL AND d.tags LIKE '%2.ADV%')               AS nb_adv,
    SUM(d.tags IS NOT NULL AND d.tags LIKE '%Injoignable%')         AS nb_injoignable,
    SUM(d.tags IS NOT NULL AND d.tags LIKE '%QUESTIONS OK%')        AS nb_questions_ok,
    SUM(d.tags IS NOT NULL AND d.tags LIKE '%BILAN POSITIF%' 
        AND d.tags NOT LIKE '%Injoignable%')                        AS nb_bilan_positif,
    SUM(d.tags IS NOT NULL AND d.tags LIKE '%BILAN MITIGE%')        AS nb_bilan_mitige,
    SUM(d.tags IS NOT NULL AND d.tags LIKE '%BILAN NEGATIF%')       AS nb_bilan_negatif,
    SUM(d.tags IS NOT NULL AND LOWER(d.tags) LIKE '%rappeler%')     AS nb_a_rappeler,
    SUM(d.tags IS NOT NULL AND d.tags LIKE '%INTERROMPU%')          AS nb_interrompu,
    -- CLIENT
    -- CLIENT seul (sans injoignable)
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.tags NOT LIKE '%Injoignable%')                        AS client_decro,
    -- CLIENT entrants
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.direction = 'inbound')                        AS client_entrants,
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.tags LIKE '%Injoignable%')                            AS client_inj,
    -- BILAN CLIENT SUIVI MISSION
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.tags LIKE '%BILAN POSITIF%'
        AND d.tags LIKE '%SUIVI MISSION%'
        AND d.tags NOT LIKE '%Injoignable%')                        AS sm_client_positif,
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.tags LIKE '%BILAN MITIGE%'
        AND d.tags LIKE '%SUIVI MISSION%')                        AS sm_client_mitige,
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.tags LIKE '%BILAN NEGATIF%'
        AND d.tags LIKE '%SUIVI MISSION%')                        AS sm_client_negatif,
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.tags LIKE '%BILAN POSITIF%'
        AND d.tags LIKE '%SUIVI MISSION%'
        AND d.tags LIKE '%Injoignable%')                        AS sm_client_inj2,
    -- BILAN CLIENT QS
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.tags LIKE '%OK%'
        AND d.tags LIKE '%QS%')                        AS qs_client_positif,
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.tags LIKE '%BILAN MITIGE%'
        AND d.tags LIKE '%QS%')                        AS qs_client_mitige,
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.tags LIKE '%BILAN NEGATIF%'
        AND d.tags LIKE '%QS%')                        AS qs_client_negatif,
    SUM(d.tags LIKE '%2.CLIENT%'
        AND d.tags LIKE '%APPEL 2%'
        AND d.tags LIKE '%QS%'
        AND d.tags LIKE '%Injoignable%')                        AS qs_client_inj2,
    -- ADV
    -- ADV seul (sans injoignable)
    SUM(d.tags LIKE '%2.ADV%'
        AND d.tags NOT LIKE '%Injoignable%')                        AS adv_decro,
    -- ADV entrants
    SUM(d.tags LIKE '%2.ADV%'
        AND d.direction = 'inbound')                        AS adv_entrants,
    SUM(d.tags LIKE '%2.ADV%'
        AND d.tags LIKE '%Injoignable%')                            AS adv_inj,
    -- BILAN ADV SUIVI MISSION
    SUM(d.tags LIKE '%2.ADV%'
        AND d.tags LIKE '%BILAN POSITIF%'
        AND d.tags LIKE '%SUIVI MISSION%'
        AND d.tags NOT LIKE '%Injoignable%')                        AS sm_adv_positif,
    SUM(d.tags LIKE '%2.ADV%'
        AND d.tags LIKE '%BILAN MITIGE%'
        AND d.tags LIKE '%SUIVI MISSION%')                        AS sm_adv_mitige,
    SUM(d.tags LIKE '%2.ADV%'
        AND d.tags LIKE '%BILAN NEGATIF%'
        AND d.tags LIKE '%SUIVI MISSION%')                        AS sm_adv_negatif,
    SUM(d.tags LIKE '%2.ADV%'
        AND d.tags LIKE '%BILAN POSITIF%'
        AND d.tags LIKE '%SUIVI MISSION%'
        AND d.tags LIKE '%Injoignable%')                        AS sm_adv_inj2,
    SUM(d.tags LIKE '%0. AUTRE%')                        AS autre,
    SUM(d.tags LIKE '%3.RAS%')                        AS ras,
    SUM(d.tags LIKE '%PRIME PARTICIPATION%')          AS nb_prime_participation
FROM data d
WHERE d.team_name = 'Suivi Qualité'
  -- AND d.direction = 'outbound' -- on considère tous les appels, pas seulement les sortants
  AND d.user IS NOT NULL
  AND d.user != '[No associated user]'
  AND d.date_only >= :df
  AND d.date_only <= :dt
