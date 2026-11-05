-- RECAP COMM : détail par conseiller
-- Params: :lines (via IN), :df, :dt
SELECT
    d.user,
    d.line,
    SUM(d.direction='inbound' AND d.user IS NOT NULL
        AND d.user != '[No associated user]')               AS pris,
    SUM(d.direction='outbound' AND d.user IS NOT NULL
        AND d.user != '[No associated user]')               AS sortants,
    SUM(d.duration_in_call_sec)                             AS total_incall,
    SUM(d.direction='inbound' AND d.user IS NOT NULL
        AND d.user != '[No associated user]')
    + SUM(d.direction='outbound' AND d.user IS NOT NULL
        AND d.user != '[No associated user]')               AS total
FROM data d
WHERE d.line IN (:lines)
  AND d.date_only >= :df
  AND d.date_only <= :dt
  AND d.user IS NOT NULL
  AND d.user != '[No associated user]'
GROUP BY d.user /*, d.line*/ /*décommenter pour découper par ligne*/
ORDER BY total DESC
