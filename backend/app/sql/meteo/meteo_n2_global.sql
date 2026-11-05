-- TCD DEB-N2 : stats globales équipe N2
-- Params: :df, :dt
SELECT
    COUNT(*)                                                    AS total_appels,
    SUM(d.direction='inbound' AND d.user IS NOT NULL
        AND d.user != '[No associated user]')                   AS pris,
    SUM(d.direction='outbound' AND d.user IS NOT NULL
        AND d.user != '[No associated user]')                   AS sortants,
    SUM(d.direction='outbound' AND d.user IS NULL
        AND d.out_of_hours = 0)                                 AS rebascules,
    SUM(d.direction='inbound'
        AND d.user = '[No associated user]')                    AS abandonnes,
    SUM(d.out_of_hours = 1)                                     AS hors_horaires,
    ROUND(
        SUM(d.direction='inbound' AND d.user IS NOT NULL
            AND d.user != '[No associated user]') * 100.0
        / NULLIF(
            SUM(d.direction='inbound' AND d.user IS NOT NULL
                AND d.user != '[No associated user]')
            + SUM(d.direction='outbound' AND d.user IS NULL
                AND d.out_of_hours = 0),
        0),
    4)                                                          AS taux_reponse,
    -- DEVIS OK
    SUM(d.tags LIKE '%DEVIS OK%')                        AS devis_ok,
    -- DEVIS KO
    SUM(d.tags LIKE '%DEVIS KO%')                        AS devis_ko,
    COUNT(DISTINCT CASE
        WHEN d.user IS NOT NULL AND d.user != '[No associated user]'
        THEN d.user END)                                        AS nb_agents
FROM data d
WHERE d.team_name = 'N2'
  AND d.date_only >= :df
  AND d.date_only <= :dt
