"""
Root conftest for all tests.

This file is intentionally minimal. Test-specific fixtures are defined in:
- tests/unit/conftest.py - Unit tests with mocked Supabase
- tests/integration/conftest.py - Integration tests with real local Supabase
"""
import sys
from pathlib import Path

# Add backend directory to path for all tests
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))
