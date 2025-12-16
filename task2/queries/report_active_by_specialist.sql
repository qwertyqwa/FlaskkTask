SELECT
  u.full_name AS specialist_full_name,
  COUNT(*) AS active_tickets_count
FROM tickets t
JOIN users u ON u.id = t.assigned_specialist_user_id
JOIN ticket_statuses ts ON ts.id = t.status_id
WHERE ts.is_final = 0
GROUP BY u.id
ORDER BY active_tickets_count DESC, specialist_full_name ASC;

