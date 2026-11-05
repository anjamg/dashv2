-- RECAP COMM : stats globales par groupe de lignes téléphoniques (SVI)
-- Params: listes IN pour l1/l2 + plages de dates
SELECT
    SUM(d.direction='inbound' AND d.user IS NOT NULL
        AND d.user != '[No associated user]')               AS pris,
    SUM(d.direction='outbound' AND d.user IS NULL
        AND d.out_of_hours = 0)                             AS rebascules,
    SUM(d.direction='inbound'
        AND d.user = '[No associated user]')                AS abandonnes,
    SUM(d.direction='outbound' AND d.user IS NOT NULL
        AND d.user != '[No associated user]')               AS sortants,
    (
        SELECT ROUND(SUM(etp), 4)
        FROM (
            SELECT
                CASE
                    WHEN COALESCE(agent_hours.productive_hours, 0) >= COALESCE(user_cfg.heures_attendues, 8)
                    THEN 1
                    ELSE ROUND(COALESCE(agent_hours.productive_hours, 0) / NULLIF(COALESCE(user_cfg.heures_attendues, 8), 0), 4)
                END AS etp
            FROM (
                SELECT
                    hourly.user,
                    COUNT(*) AS productive_hours
                FROM (
                    SELECT
                        d2.user,
                        DATE(d2.datetime_tz_offset_incl) AS work_date,
                        HOUR(d2.datetime_tz_offset_incl) AS work_hour
                    FROM data d2
                    WHERE d2.line IN (:lines1)
                      AND d2.date_only >= :df1
                      AND d2.date_only <= :dt1
                      AND d2.user IS NOT NULL
                      AND d2.user != '[No associated user]'
                    GROUP BY d2.user, DATE(d2.datetime_tz_offset_incl), HOUR(d2.datetime_tz_offset_incl)
                    HAVING COUNT(*) > 1
                ) hourly
                GROUP BY hourly.user
            ) agent_hours
            LEFT JOIN users user_cfg
                ON user_cfg.agent_name = agent_hours.user
               OR user_cfg.username = agent_hours.user
        ) agent_etp
    ) AS effectifs
FROM data d
WHERE d.line IN (:lines2)
  AND d.date_only >= :df2
  AND d.date_only <= :dt2
