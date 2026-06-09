-- Add display-ready BOQ hierarchy fields.
-- Existing rows keep their current WBS level and are marked OK until re-sync.

ALTER TABLE boq_items
ADD COLUMN IF NOT EXISTS raw_wbs_level INTEGER,
ADD COLUMN IF NOT EXISTS display_wbs_level INTEGER,
ADD COLUMN IF NOT EXISTS row_type VARCHAR,
ADD COLUMN IF NOT EXISTS hierarchy_status VARCHAR,
ADD COLUMN IF NOT EXISTS source_row_index INTEGER,
ADD COLUMN IF NOT EXISTS sort_order INTEGER;

UPDATE boq_items
SET
    raw_wbs_level = COALESCE(raw_wbs_level, wbs_level),
    display_wbs_level = COALESCE(display_wbs_level, wbs_level),
    row_type = COALESCE(
        row_type,
        CASE
            WHEN lower(coalesce(description, '')) LIKE 'total%'
                OR lower(coalesce(item_no, '')) LIKE 'total%'
                OR lower(coalesce(description, '')) LIKE 'รวม%'
            THEN 'TOTAL'
            WHEN coalesce(wbs_level, 1) <= 1 THEN 'SYSTEM'
            WHEN coalesce(wbs_level, 1) = 2 THEN 'GROUP'
            ELSE 'ITEM'
        END
    ),
    hierarchy_status = COALESCE(hierarchy_status, 'OK'),
    source_row_index = COALESCE(source_row_index, 0),
    sort_order = COALESCE(sort_order, 0)
WHERE raw_wbs_level IS NULL
    OR display_wbs_level IS NULL
    OR row_type IS NULL
    OR hierarchy_status IS NULL
    OR source_row_index IS NULL
    OR sort_order IS NULL;

CREATE INDEX IF NOT EXISTS ix_boq_items_active_hierarchy_order
ON boq_items (project_id, boq_type, sheet_name, valid_to, sort_order, source_row_index);
