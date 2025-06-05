import sqlite3
import uuid

conn = sqlite3.connect("typing_data.db")
c = conn.cursor()

# 1. Populate categories with new UUIDs
c.execute("SELECT * FROM categories_old")
categories = c.fetchall()
cat_map = {}
for row in categories:
    old_id, name = row[:2]
    new_id = str(uuid.uuid4())
    cat_map[old_id] = new_id
    c.execute(
        "INSERT INTO categories (category_id_new, category_name) VALUES (?, ?)", (new_id, name)
    )

# 2. Populate snippets with new UUIDs and new category_id
c.execute("SELECT * FROM snippets_old")
snippets = c.fetchall()
snip_map = {}
for row in snippets:
    old_id, old_cat_id, name = row[:3]
    new_id = str(uuid.uuid4())
    snip_map[old_id] = new_id
    new_cat_id = cat_map[old_cat_id]
    c.execute(
        "INSERT INTO snippets (snippet_id_new, category_id_new, snippet_name) VALUES (?, ?, ?)",
        (new_id, new_cat_id, name),
    )

# 3. Populate snippet_parts with new UUIDs and new snippet_id
c.execute("SELECT * FROM snippet_parts_old")
parts = c.fetchall()
for row in parts:
    old_part_id, old_snip_id, part_number, content = row[:4]
    new_part_id = str(uuid.uuid4())
    new_snip_id = snip_map[old_snip_id]
    c.execute(
        "INSERT INTO snippet_parts (part_id_new, snippet_id_new, part_number, content) VALUES (?, ?, ?, ?)",
        (new_part_id, new_snip_id, part_number, content),
    )

conn.commit()
conn.close()
print("Step 3 migration complete.")
