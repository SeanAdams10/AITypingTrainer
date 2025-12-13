
import pytest
from unittest.mock import MagicMock
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from db.exceptions import ConstraintError

class TestKeysetRepositoryConstraints:
    """Test that PostgresKeysetRepository correctly wraps database constraints."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_db):
        return PostgresKeysetRepository(mock_db)

    def test_save_wraps_unique_name_constraint(self, repo, mock_db):
        """Test that duplicate keyset name raises ValueError with friendly message."""
        keyset = Keyset(
            keyboard_id="123",
            keyset_name="Duplicate Name",
            progression_order=1,
            keys=[]
        )
        
        # Mock database to raise ConstraintError for name
        mock_db.execute.side_effect = ConstraintError("unique constraint \"keyset_keyboard_id_keyset_name_key\" violation")
        mock_db.fetchone.return_value = None # simulate new record

        with pytest.raises(ValueError) as exc_info:
            repo.save(keyset, updated_by="00000000-0000-0000-0000-000000000001")
        
        assert "Keyset name 'Duplicate Name' already exists" in str(exc_info.value)

    def test_save_wraps_unique_progression_constraint(self, repo, mock_db):
        """Test that duplicate progression order raises ValueError with friendly message."""
        keyset = Keyset(
            keyboard_id="123",
            keyset_name="New Name",
            progression_order=5,
            keys=[]
        )
        
        # Mock database to raise ConstraintError for progression
        mock_db.execute.side_effect = ConstraintError("unique constraint \"keyset_keyboard_id_progression_order_key\" violation")
        mock_db.fetchone.return_value = None

        with pytest.raises(ValueError) as exc_info:
            repo.save(keyset, updated_by="00000000-0000-0000-0000-000000000001")
            
        assert "Progression order 5 is already in use" in str(exc_info.value)

    def test_save_wraps_generic_constraint(self, repo, mock_db):
        """Test that other constraints raise informative ValueError."""
        keyset = Keyset(
            keyboard_id="123",
            keyset_name="Name",
            progression_order=1,
            keys=[]
        )
        
        mock_db.execute.side_effect = ConstraintError("some other constraint")
        mock_db.fetchone.return_value = None

        with pytest.raises(ValueError) as exc_info:
            repo.save(keyset, updated_by="00000000-0000-0000-0000-000000000001")
            

if __name__ == "__main__":
    t = TestKeysetRepositoryConstraints()
    db = MagicMock()
    repo = PostgresKeysetRepository(db)
    
    print("Running test_save_wraps_unique_name_constraint...")
    t.test_save_wraps_unique_name_constraint(repo, db)
    print("PASS")

    print("Running test_save_wraps_unique_progression_constraint...")
    t.test_save_wraps_unique_progression_constraint(repo, db)
    print("PASS")

    print("Running test_save_wraps_generic_constraint...")
    t.test_save_wraps_generic_constraint(repo, db)
    print("PASS")
