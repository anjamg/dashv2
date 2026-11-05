-- TCD DEB-N2 : stats par agent
-- Params: :df, :dt
SELECT
    d.user,
    COUNT(*)                                                    AS total,
    SUM(d.direction='inbound' AND d.user IS NOT NULL
        AND d.user != '[No associated user]')                   AS pris,
    SUM(d.direction='outbound' AND d.user IS NOT NULL
        AND d.user != '[No associated user]')                   AS sortants,
    SUM(d.direction='outbound' AND d.user IS NULL
        AND d.out_of_hours = 0)                                 AS rebascules,
    COALESCE(SUM(d.duration_in_call_sec), 0)                     AS total_incall,
    ROUND(AVG(CASE
        WHEN d.direction='inbound' AND d.user IS NOT NULL
             AND d.user != '[No associated user]'
        THEN d.duration_in_call_sec END))                       AS avg_incall
FROM data d
WHERE d.team_name = 'N2'
  AND d.date_only >= :df
  AND d.date_only <= :dt
  AND d.user IS NOT NULL
  AND d.user != '[No associated user]'
GROUP BY d.user
ORDER BY total DESC
