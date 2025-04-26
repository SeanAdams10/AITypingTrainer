import sqlite3

# Connect to the database
conn = sqlite3.connect('typing_data.db')
cursor = conn.cursor()

# Drop the specified tables
cursor.execute("DROP TABLE IF EXISTS session_bigram_error")
print("Dropped session_bigram_error table")

cursor.execute("DROP TABLE IF EXISTS session_bigram_speed")
print("Dropped session_bigram_speed table")

# Drop the trigram tables
cursor.execute("DROP TABLE IF EXISTS session_trigram_error")
print("Dropped session_trigram_error table")

cursor.execute("DROP TABLE IF EXISTS session_trigram_speed")
print("Dropped session_trigram_speed table")

# Commit the changes and close the connection
conn.commit()
conn.close()
print("Database operations completed successfully")
