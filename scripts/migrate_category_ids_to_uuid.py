"""
Migration script to convert category_id from INTEGER to UUID in categories and snippets tables.
Preserves all data and relationships.
"""
import sqlite3
import uuid

DB_PATH = "typing_data.db"  # Change if needed

def migrate_category_ids(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Read all categories and build mapping old_id -> new_uuid
    cur.execute("SELECT category_id, category_name FROM categories")
    categories = cur.fetchall()
    id_map = {row[0]: str(uuid.uuid4()) for row in categories}
    
    # 2. Add new UUID column to categories
    cur.execute("ALTER TABLE categories ADD COLUMN category_id_new TEXT")
    for old_id, new_uuid in id_map.items():
        cur.execute("UPDATE categories SET category_id_new = ? WHERE category_id = ?", (new_uuid, old_id))
    
    # 3. Add new UUID column to snippets
    cur.execute("ALTER TABLE snippets ADD COLUMN category_id_new TEXT")
    for old_id, new_uuid in id_map.items():
        cur.execute("UPDATE snippets SET category_id_new = ? WHERE category_id = ?", (new_uuid, old_id))
    
    # 4. Create new categories table with UUID PK
    cur.execute("""
        CREATE TABLE categories_new (
            category_id TEXT PRIMARY KEY,
            category_name TEXT NOT NULL UNIQUE
        )
    """)
    cur.execute("INSERT INTO categories_new (category_id, category_name) SELECT category_id_new, category_name FROM categories")
    
    # 5. Create new snippets table with UUID FK
    cur.execute("""
        CREATE TABLE snippets_new (
            snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id TEXT NOT NULL,
            snippet_name TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories_new(category_id) ON DELETE CASCADE,
            UNIQUE (category_id, snippet_name)
        )
    """)
    cur.execute("INSERT INTO snippets_new (snippet_id, category_id, snippet_name) SELECT snippet_id, category_id_new, snippet_name FROM snippets")
    
    # 6. Drop old tables and rename new ones
    cur.execute("DROP TABLE snippets")
    cur.execute("ALTER TABLE snippets_new RENAME TO snippets")
    cur.execute("DROP TABLE categories")
    cur.execute("ALTER TABLE categories_new RENAME TO categories")
    
    conn.commit()
    conn.close()
    print("Migration complete. All category_ids are now UUIDs.")

if __name__ == "__main__":
    migrate_category_ids(DB_PATH)
