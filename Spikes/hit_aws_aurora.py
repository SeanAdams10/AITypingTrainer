import boto3
import psycopg2

region = "us-east-1"
secret_name = "Aurora/WBTT_Config"

# Retrieve secret
sm_client = boto3.client("secretsmanager", region_name=region)
secret = sm_client.get_secret_value(SecretId=secret_name)
cfg = eval(secret["SecretString"])

# Generate auth token
rds = boto3.client("rds", region_name=region)
token = rds.generate_db_auth_token(
    DBHostname=cfg["host"], Port=int(cfg["port"]), DBUsername=cfg["username"], Region=region
)

print("DB Name:", cfg["dbname"])
print("DB Host:", cfg["host"])
print("DB Port:", cfg["port"])
print("DB User:", cfg["username"])

# Connect
conn = psycopg2.connect(
    host=cfg["host"],
    port=cfg["port"],
    database=cfg["dbname"],
    user=cfg["username"],
    password=token,
    sslmode="require",
)
cur = conn.cursor()

# Create table
cur.execute("""
CREATE TABLE IF NOT EXISTS typing.TestTable (
    id SERIAL PRIMARY KEY,
    name TEXT
)
""")

# Insert rows
cur.execute("""INSERT INTO typing.TestTable(name) VALUES (%s),(%s)""", ("First Row", "Second Row"))

# Query rows
cur.execute("""SELECT * FROM typing.TestTable """)
rows = cur.fetchall()
for row in rows:
    print("Row:", row)

# # Query rows
# cur.execute(r"SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'typing';")
# rows = cur.fetchall()
# if cur.rowcount == 0:
#     print("No rows returned")
# for row in rows:
#     print("Row:", row)


conn.commit()
cur.close()
conn.close()
