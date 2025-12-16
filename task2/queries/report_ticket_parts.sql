SELECT
  t.request_number,
  p.name AS part_name,
  tp.quantity,
  u.full_name AS created_by,
  tp.created_at
FROM ticket_parts tp
JOIN tickets t ON t.id = tp.ticket_id
JOIN parts p ON p.id = tp.part_id
JOIN users u ON u.id = tp.created_by_user_id
ORDER BY t.request_number ASC, tp.created_at ASC;

