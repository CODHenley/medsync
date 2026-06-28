-- Lincoln Park weekly spend 2026 (from Vetcove Weekly Budgets screen)
-- One row per week. purchased_at = week start date so the analytics date
-- range filter naturally sums only the weeks within the selected period.
-- Replaces the old YTD aggregate row for Lincoln Park.

DELETE FROM purchase_history
WHERE location_id = '11111111-0000-0000-0000-000000000001'
  AND source IN ('vetcove', 'vetcove_weekly');

INSERT INTO purchase_history (location_id, vendor, amount, purchased_at, source, note, period_month)
VALUES
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3983.00, '2025-12-29', 'vetcove_weekly', 'Week 1 2026 (Dec 29 – Jan 04)',  '2026-01'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  5081.00, '2026-01-05', 'vetcove_weekly', 'Week 2 2026 (Jan 05 – Jan 11)',  '2026-01'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3277.00, '2026-01-12', 'vetcove_weekly', 'Week 3 2026 (Jan 12 – Jan 18)',  '2026-01'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3827.00, '2026-01-19', 'vetcove_weekly', 'Week 4 2026 (Jan 19 – Jan 25)',  '2026-01'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3278.00, '2026-01-26', 'vetcove_weekly', 'Week 5 2026 (Jan 26 – Feb 01)',  '2026-01'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  5064.00, '2026-02-02', 'vetcove_weekly', 'Week 6 2026 (Feb 02 – Feb 08)',  '2026-02'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  2715.00, '2026-02-09', 'vetcove_weekly', 'Week 7 2026 (Feb 09 – Feb 15)',  '2026-02'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3814.00, '2026-02-16', 'vetcove_weekly', 'Week 8 2026 (Feb 16 – Feb 22)',  '2026-02'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  4440.00, '2026-02-23', 'vetcove_weekly', 'Week 9 2026 (Feb 23 – Mar 01)',  '2026-02'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  4523.00, '2026-03-02', 'vetcove_weekly', 'Week 10 2026 (Mar 02 – Mar 08)', '2026-03'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3246.00, '2026-03-09', 'vetcove_weekly', 'Week 11 2026 (Mar 09 – Mar 15)', '2026-03'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3926.00, '2026-03-16', 'vetcove_weekly', 'Week 12 2026 (Mar 16 – Mar 22)', '2026-03'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  4054.00, '2026-03-23', 'vetcove_weekly', 'Week 13 2026 (Mar 23 – Mar 29)', '2026-03'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  4263.00, '2026-03-30', 'vetcove_weekly', 'Week 14 2026 (Mar 30 – Apr 05)', '2026-03'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3889.00, '2026-04-06', 'vetcove_weekly', 'Week 15 2026 (Apr 06 – Apr 12)', '2026-04'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  4403.00, '2026-04-13', 'vetcove_weekly', 'Week 16 2026 (Apr 13 – Apr 19)', '2026-04'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  6111.00, '2026-04-20', 'vetcove_weekly', 'Week 17 2026 (Apr 20 – Apr 26)', '2026-04'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3250.00, '2026-04-27', 'vetcove_weekly', 'Week 18 2026 (Apr 27 – May 03)', '2026-04'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3571.00, '2026-05-04', 'vetcove_weekly', 'Week 19 2026 (May 04 – May 10)', '2026-05'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  4412.00, '2026-05-11', 'vetcove_weekly', 'Week 20 2026 (May 11 – May 17)', '2026-05'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  4273.00, '2026-05-18', 'vetcove_weekly', 'Week 21 2026 (May 18 – May 24)', '2026-05'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  4757.00, '2026-05-25', 'vetcove_weekly', 'Week 22 2026 (May 25 – May 31)', '2026-05'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  4367.00, '2026-06-01', 'vetcove_weekly', 'Week 23 2026 (Jun 01 – Jun 07)', '2026-06'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3991.00, '2026-06-08', 'vetcove_weekly', 'Week 24 2026 (Jun 08 – Jun 14)', '2026-06'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  5173.00, '2026-06-15', 'vetcove_weekly', 'Week 25 2026 (Jun 15 – Jun 21)', '2026-06'),
  ('11111111-0000-0000-0000-000000000001', 'Vetcove',  3742.00, '2026-06-22', 'vetcove_weekly', 'Week 26 2026 (Jun 22 – Jun 28)', '2026-06');

-- LP YTD total: $107,430
