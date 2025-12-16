SELECT
  COALESCE(ft.name, 'Не указано') AS fault_type_name,
  COUNT(*) AS completed_count
FROM tickets t
JOIN ticket_statuses ts ON ts.id = t.status_id
LEFT JOIN fault_types ft ON ft.id = t.fault_type_id
WHERE ts.code = 'completed'
  AND t.completed_at IS NOT NULL
  AND t.completed_at BETWEEN :date_from AND :date_to
GROUP BY ft.name
ORDER BY completed_count DESC, fault_type_name ASC;

