SELECT
  COUNT(*) AS completed_count,
  ROUND(AVG((julianday(t.completed_at) - julianday(t.created_at)) * 86400)) AS avg_duration_seconds
FROM tickets t
JOIN ticket_statuses ts ON ts.id = t.status_id
WHERE ts.code = 'completed'
  AND t.completed_at IS NOT NULL
  AND t.completed_at BETWEEN :date_from AND :date_to;

