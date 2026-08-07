SELECT
    allocation.id,
    allocation.reference_no,
    allocation.amount,
    COALESCE(SUM(CASE WHEN ledger.direction = 'DEBIT' THEN ledger.amount ELSE 0 END), 0) AS debit_total,
    COALESCE(SUM(CASE WHEN ledger.direction = 'CREDIT' THEN ledger.amount ELSE 0 END), 0) AS credit_total,
    COUNT(ledger.id) AS ledger_entry_count
FROM fund_allocations AS allocation
LEFT JOIN fund_ledger_entries AS ledger ON ledger.allocation_id = allocation.id
GROUP BY allocation.id, allocation.reference_no, allocation.amount
HAVING
    COUNT(ledger.id) <> 2
    OR COALESCE(SUM(CASE WHEN ledger.direction = 'DEBIT' THEN ledger.amount ELSE 0 END), 0) <> allocation.amount
    OR COALESCE(SUM(CASE WHEN ledger.direction = 'CREDIT' THEN ledger.amount ELSE 0 END), 0) <> allocation.amount
ORDER BY allocation.created_at DESC;
