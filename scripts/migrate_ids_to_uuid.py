"""
Migration script to convert category_id and snippet_id from INTEGER to UUID (TEXT) in the database.
- Migrates both categories and snippets tables.
- Preserves all data and relationships.
- Can be run safely on an existing DB.

Usage:
    python scripts/migrate_ids_to_uuid.py <path_to_db>
"""
import sys
import sqlite3
import uuid

def migrate_categories_and_snippets(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Add new UUID columns
    cur.execute("ALTER TABLE categories ADD COLUMN category_id_new TEXT")
    cur.execute("ALTER TABLE snippets ADD COLUMN snippet_id_new TEXT")
    cur.execute("ALTER TABLE snippets ADD COLUMN category_id_new TEXT")

    # 2. Generate UUIDs for all categories
    cur.execute("SELECT category_id FROM categories")
    cat_id_map = {}
    for row in cur.fetchall():
        old_id = row[0]
        new_id = str(uuid.uuid4())
        cat_id_map[old_id] = new_id
        cur.execute("UPDATE categories SET category_id_new = ? WHERE category_id = ?", (new_id, old_id))

    # 3. Update snippets with new UUIDs and new category UUIDs
    cur.execute("SELECT snippet_id, category_id FROM snippets")
    for row in cur.fetchall():
        old_snip_id, old_cat_id = row
        new_snip_id = str(uuid.uuid4())
        new_cat_id = cat_id_map[old_cat_id]
        cur.execute("UPDATE snippets SET snippet_id_new = ?, category_id_new = ? WHERE snippet_id = ?", (new_snip_id, new_cat_id, old_snip_id))

    # 4. Create new tables with UUIDs as primary keys
    cur.execute("""
        CREATE TABLE categories_new (
            category_id TEXT PRIMARY KEY,
            category_name TEXT NOT NULL UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE snippets_new (
            snippet_id TEXT PRIMARY KEY,
            category_id TEXT NOT NULL,
            snippet_name TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories_new(category_id) ON DELETE CASCADE,
            UNIQUE (category_id, snippet_name)
        )
    """)

    # 5. Copy data to new tables
    cur.execute("INSERT INTO categories_new (category_id, category_name) SELECT category_id_new, category_name FROM categories")
    cur.execute("INSERT INTO snippets_new (snippet_id, category_id, snippet_name) SELECT snippet_id_new, category_id_new, snippet_name FROM snippets")

    # 6. Drop old tables and rename new ones
    cur.execute("DROP TABLE snippets")
    cur.execute("DROP TABLE categories")
    cur.execute("ALTER TABLE categories_new RENAME TO categories")
    cur.execute("ALTER TABLE snippets_new RENAME TO snippets")

    conn.commit()
    conn.close()
    print("Migration complete. All IDs are now UUIDs.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python migrate_ids_to_uuid.py <path_to_db>")
        sys.exit(1)
    migrate_categories_and_snippets(sys.argv[1])
