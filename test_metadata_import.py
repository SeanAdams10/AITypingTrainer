#!/usr/bin/env python3
"""Test script to verify metadata import."""

from repositories.metadata import metadata

print("✓ Metadata imported successfully:", metadata)
print("✓ Metadata type:", type(metadata))
print("✓ Phase 0 complete: Folder structure and shared metadata created")
