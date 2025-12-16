SELECT
  t.request_number,
  u.full_name AS author_full_name,
  c.created_at,
  c.body
FROM ticket_comments c
JOIN tickets t ON t.id = c.ticket_id
JOIN users u ON u.id = c.user_id
ORDER BY t.request_number ASC, c.created_at ASC;

