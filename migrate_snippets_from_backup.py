import sqlite3

from db.database_manager import DatabaseManager
from models.category_manager import CategoryManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager

# Paths
backup_db = "typing_data_backup.db"
target_db = "typing_data.db"

# Open connections
backup_conn = sqlite3.connect(backup_db)
backup_c = backup_conn.cursor()

target_dbm = DatabaseManager(target_db)
cat_mgr = CategoryManager(target_dbm)
snip_mgr = SnippetManager(target_dbm)

# Build a mapping from old category name to new UUID in the new DB
cat_name_to_uuid = {cat.category_name: cat.category_id for cat in cat_mgr.list_all_categories()}

# 1. Migrate snippets
backup_c.execute("SELECT snippet_id, category_id, snippet_name FROM snippets")
snippet_rows = backup_c.fetchall()
old_snip_id_to_new = {}
for old_snip_id, old_cat_id, snippet_name in snippet_rows:
    # Lookup category name in backup DB
    backup_c.execute("SELECT category_name FROM categories WHERE category_id=?", (old_cat_id,))
    row = backup_c.fetchone()
    if not row:
        print(f"Skipping snippet {snippet_name}: category_id {old_cat_id} not found in backup.")
        continue
    cat_name = row[0]
    new_cat_id = cat_name_to_uuid.get(cat_name)
    if not new_cat_id:
        print(f"Skipping snippet {snippet_name}: category '{cat_name}' not found in new DB.")
        continue
    # Create snippet in new DB
    snippet = Snippet(category_id=new_cat_id, snippet_name=snippet_name, content="")
    snip_mgr.save_snippet(snippet)
    old_snip_id_to_new[old_snip_id] = snippet.snippet_id

# 2. Migrate snippet_parts
backup_c.execute("SELECT part_id, snippet_id, part_number, content FROM snippet_parts")
part_rows = backup_c.fetchall()
for part_id, old_snip_id, part_number, content in part_rows:
    new_snip_id = old_snip_id_to_new.get(old_snip_id)
    if not new_snip_id:
        print(f"Skipping snippet_part {part_id}: snippet_id {old_snip_id} not found in new DB.")
        continue
    # Use SnippetManager to add content to the snippet (append to content)
    snippet = snip_mgr.get_snippet_by_id(new_snip_id)
    if snippet:
        if snippet.content:
            snippet.content += content
        else:
            snippet.content = content
        snip_mgr.save_snippet(snippet)

print("Migration of snippets and snippet_parts complete.")
