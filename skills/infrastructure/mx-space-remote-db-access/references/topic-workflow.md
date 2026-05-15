# Topic / Notes Workflow

`notes.topic_id` is a `text` fk to `topics(id)` with `ON DELETE SET NULL`. Use this for assignment audits.

## Inventory

```sql
SELECT t.name, t.slug,
       (SELECT COUNT(*) FROM notes n WHERE n.topic_id = t.id) AS notes
FROM topics t
ORDER BY name;
```

## Unassigned notes

```sql
SELECT nid, title, LEFT(text, 200) AS excerpt
FROM notes
WHERE topic_id IS NULL
ORDER BY nid DESC;
```

## Guarded assignment

Always include the null guard **and** an explicit `nid` list, run inside a transaction:

```sql
BEGIN;

UPDATE notes
SET topic_id = (SELECT id FROM topics WHERE name = 'Tech')
WHERE topic_id IS NULL
  AND nid = ANY(ARRAY[12, 11, 9]);

SELECT nid, topic_id FROM notes WHERE nid = ANY(ARRAY[12, 11, 9]);

COMMIT;
```

The null guard prevents accidental reassignment of already-classified notes.
