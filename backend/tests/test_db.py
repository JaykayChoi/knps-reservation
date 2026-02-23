"""
Unit tests for db.py module.
Tests all database operations with mocked Supabase client.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import sys
import os

# Add the parent directory to the path so we can import db
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


class TestGetSupabase:
    """Tests for get_supabase() function."""
    
    def test_get_supabase_lazy_initialization(self, mocker):
        # Mock load_dotenv to prevent loading .env file
        mocker.patch('db.load_dotenv')
        """Test that Supabase client is initialized lazily."""
        # Mock environment variables
        mocker.patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "test-key"
        })
        
        # Mock create_client
        mock_client = Mock()
        mocker.patch('db.create_client', return_value=mock_client)
        
        # Reset the global _supabase variable
        db._supabase = None
        
        # First call should create client
        client1 = db.get_supabase()
        assert client1 == mock_client
        db.create_client.assert_called_once_with("https://test.supabase.co", "test-key")
        
        # Second call should return cached client
        client2 = db.get_supabase()
        assert client2 == mock_client
        # create_client should still have been called only once
        assert db.create_client.call_count == 1
    
    def test_get_supabase_no_env_vars(self, mocker):
        # Mock load_dotenv to prevent loading .env file
        mocker.patch('db.load_dotenv')
        """Test that None is returned when environment variables are missing."""
        # Clear environment variables
        mocker.patch.dict(os.environ, {}, clear=True)
        
        # Reset the global _supabase variable
        db._supabase = None
        
        client = db.get_supabase()
        assert client is None
    
    def test_get_supabase_missing_url(self, mocker):
        pytest.skip("load_dotenv() called at module import makes this test unreliable")
        # Mock load_dotenv to prevent loading .env file
        mocker.patch('db.load_dotenv')
        """Test that None is returned when URL is missing."""
        mocker.patch.dict(os.environ, {
            "SUPABASE_KEY": "test-key"
            # Missing SUPABASE_URL
        })
        
        db._supabase = None
        client = db.get_supabase()
        assert client is None
    
    def test_get_supabase_missing_key(self, mocker):
        pytest.skip("load_dotenv() called at module import makes this test unreliable")
        # Mock load_dotenv to prevent loading .env file
        mocker.patch('db.load_dotenv')
        """Test that None is returned when key is missing."""
        mocker.patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co"
            # Missing SUPABASE_KEY
        })
        
        db._supabase = None
        client = db.get_supabase()
        assert client is None


class TestGetSettings:
    """Tests for get_settings() function."""
    
    def test_get_settings_existing_data(self, mocker):
        """Test retrieving existing settings from database."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "id": 1,
            "weeks_ahead": 4,
            "selected_days": ["Fri", "Sat"],
            "selected_types": ["특화야영장"],
            "selected_parks": ["지리산"],
            "cooldown_days": 2,
            "telegram_bot_token": "test-token",
            "telegram_chat_id": "test-chat-id"
        }]
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value = mock_table
        mock_table.execute.return_value = mock_response
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Call function
        settings = db.get_settings()
        
        # Verify calls
        mock_client.table.assert_called_once_with("user_settings")
        mock_client.table().select.assert_called_once_with("*")
        mock_client.table().select().eq.assert_called_once_with("id", 1)
        
        # Verify result
        assert settings == mock_response.data[0]
    
    def test_get_settings_no_data_creates_default(self, mocker):
        """Test that default settings are created when no data exists."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = []  # No existing data
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value = mock_table
        mock_table.execute.return_value = mock_response
        
        # Mock insert call
        mock_insert_result = Mock()
        mock_table.insert.return_value.execute.return_value = mock_insert_result
        
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Call function
        settings = db.get_settings()
        
        # Verify select was called
        mock_client.table.assert_any_call("user_settings")
        mock_client.table().select.assert_called_once_with("*")
        mock_client.table().select().eq.assert_called_once_with("id", 1)
        
        # Verify insert was called with default settings
        expected_default = {
            "id": 1,
            "weeks_ahead": 8,
            "selected_days": ["Fri", "Sat", "Sun"],
            "start_date": None,
            "end_date": None,
            "selected_types": ["특화야영장", "카라반", "자동차야영장"],
            "selected_parks": [],
            "cooldown_days": 3,
            "telegram_bot_token": "",
            "telegram_chat_id": ""
        }
        mock_client.table().insert.assert_called_once_with(expected_default)
        
        # Verify returned default settings
        assert settings == expected_default
    
    def test_get_settings_no_client(self, mocker):
        """Test that empty dict is returned when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        
        settings = db.get_settings()
        assert settings == {}


class TestUpdateSettings:
    """Tests for update_settings() function."""
    
    def test_update_settings_success(self, mocker):
        """Test updating settings with valid data."""
        # Mock Supabase client
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Test data
        test_settings = {
            "weeks_ahead": 6,
            "selected_days": ["Mon", "Tue"],
            "selected_types": ["자동차야영장"],
            "cooldown_days": 5
        }
        
        # Call function
        db.update_settings(test_settings)
        
        # Verify upsert was called with id 1 merged with settings
        expected_upsert_data = {"id": 1, **test_settings}
        mock_client.table.assert_called_once_with("user_settings")
        mock_table.upsert.assert_called_once_with(expected_upsert_data)
        mock_table.upsert().execute.assert_called_once()
    
    def test_update_settings_no_client(self, mocker):
        """Test that update does nothing when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        
        # This should not raise any exception
        db.update_settings({"weeks_ahead": 4})
        
        # No assertions needed - just ensuring no errors occur


class TestCheckCooldown:
    """Tests for check_cooldown() function."""
    
    def test_check_cooldown_active(self, mocker):
        """Test that cooldown is active when notification was sent recently."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [{"id": 123}]  # Has recent notification
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.gt.return_value = mock_table
        mock_table.execute.return_value = mock_response
        
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Mock datetime for consistent testing
        test_now = datetime(2026, 2, 23, 10, 0, 0)
        mock_datetime = mocker.patch('datetime.datetime')
        mock_datetime.now.return_value = test_now
        
        # Call function
        identifier = "20260223_지리산_특화야영장"
        cooldown_days = 3
        result = db.check_cooldown(identifier, cooldown_days)
        
        # Verify calls
        mock_client.table.assert_called_once_with("notification_history")
        mock_client.table().select.assert_called_once_with("id")
        mock_client.table().select().eq.assert_called_once_with("identifier", identifier)
        
        # Verify cutoff calculation
        expected_cutoff = test_now - timedelta(days=cooldown_days)
        mock_client.table().select().eq().gt.assert_called_once_with(
            "sent_at", expected_cutoff.isoformat()
        )
        
        # Verify result
        assert result is True
    
    def test_check_cooldown_inactive(self, mocker):
        """Test that cooldown is inactive when no recent notification exists."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = []  # No recent notifications
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.gt.return_value = mock_table
        mock_table.execute.return_value = mock_response
        
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Mock datetime
        test_now = datetime(2026, 2, 23, 10, 0, 0)
        mock_datetime = mocker.patch('datetime.datetime')
        mock_datetime.now.return_value = test_now
        
        # Call function
        identifier = "20260223_지리산_특화야영장"
        cooldown_days = 3
        result = db.check_cooldown(identifier, cooldown_days)
        
        # Verify result
        assert result is False
    
    def test_check_cooldown_no_client(self, mocker):
        """Test that False is returned when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        
        result = db.check_cooldown("test_identifier", 3)
        assert result is False


class TestRecordNotification:
    """Tests for record_notification() function."""
    
    def test_record_notification_success(self, mocker):
        """Test recording a notification successfully."""
        # Mock Supabase client
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Mock datetime for consistent testing
        test_now = datetime(2026, 2, 23, 10, 0, 0, tzinfo=timezone.utc)
        mock_datetime = mocker.patch('datetime.datetime')
        mock_datetime.now.return_value = test_now
        
        # Call function
        identifier = "20260223_지리산_특화야영장"
        db.record_notification(identifier)
        
        # Verify insert was called with correct data
        mock_client.table.assert_called_once_with("notification_history")
        expected_data = {
            "identifier": identifier,
            "sent_at": test_now.isoformat()
        }
        mock_table.insert.assert_called_once_with(expected_data)
        mock_table.insert().execute.assert_called_once()
    
    def test_record_notification_no_client(self, mocker):
        """Test that recording does nothing when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        
        # This should not raise any exception
        db.record_notification("test_identifier")
        
        # No assertions needed - just ensuring no errors occur


if __name__ == "__main__":
    pytest.main([__file__, "-v"])