SELECT
  t.request_number,
  t.created_at,
  c.full_name AS customer_full_name,
  c.phone AS customer_phone,
  et.name AS equipment_type,
  em.name AS equipment_model,
  ts.name AS status_name,
  ft.name AS fault_type_name,
  opened.full_name AS opened_by,
  specialist.full_name AS assigned_specialist,
  t.completed_at
FROM tickets t
JOIN customers c ON c.id = t.customer_id
JOIN equipment_models em ON em.id = t.equipment_model_id
JOIN equipment_types et ON et.id = em.equipment_type_id
JOIN ticket_statuses ts ON ts.id = t.status_id
LEFT JOIN fault_types ft ON ft.id = t.fault_type_id
JOIN users opened ON opened.id = t.opened_by_user_id
LEFT JOIN users specialist ON specialist.id = t.assigned_specialist_user_id
ORDER BY t.created_at DESC;

