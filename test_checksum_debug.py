"""Debug script to test checksum comparison."""
import sys
sys.path.insert(0, 'd:\\SeanDevLocal\\AITypingTrainer\\feature_keyset')

from hashlib import sha256

# Simulate what happens
keyboard_id = "test-keyboard"
keyset_name = "Home Row"
progression_order = 1

# Create checksum
payload = f"{keyboard_id}|{keyset_name}|{int(progression_order)}"
checksum_hex = sha256(payload.encode("utf-8")).hexdigest()
print(f"Original checksum (hex): {checksum_hex}")

# Convert to bytes (what we store in DB)
checksum_bytes = bytes.fromhex(checksum_hex)
print(f"Stored as bytes: {checksum_bytes!r}")

# Simulate reading from DB (PostgreSQL returns bytes)
retrieved_from_db = checksum_bytes
print(f"Retrieved from DB: {retrieved_from_db!r}")

# Convert back to hex for comparison
if isinstance(retrieved_from_db, bytes):
    retrieved_hex = retrieved_from_db.hex()
else:
    retrieved_hex = str(retrieved_from_db)
    
print(f"Retrieved as hex: {retrieved_hex}")

# New checksum (should be same since data unchanged)
new_checksum_hex = sha256(payload.encode("utf-8")).hexdigest()
print(f"New checksum (hex): {new_checksum_hex}")

# Compare
print(f"Match: {retrieved_hex == new_checksum_hex}")
