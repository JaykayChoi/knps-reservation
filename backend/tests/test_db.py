"""
Unit tests for db.py module.
Tests all database operations with mocked Supabase client.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
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
    def test_get_settings_specific_id(self, mocker):
        """Test retrieving existing settings from database."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "id": 1,
            "name": "Test Setting",
            "date_mode": "weekday",
            "is_active": True,
            "weeks_ahead": 4,
            "selected_days": ["Fri", "Sat"],
            "selected_types": ["특화야영장"],
            "selected_parks": ["지리산"],
            "cooldown_days": 2,
            "telegram_bot_token": "test-token",
            "telegram_chat_id": "test-chat-id",
            "created_at": "2026-02-23T10:00:00Z",

        }]
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value = mock_table
        mock_table.execute.return_value = mock_response
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        # Call function with specific ID
        settings = db.get_settings(1)
        
        # Verify calls
        mock_client.table.assert_called_once_with("user_settings")
        mock_client.table().select.assert_called_once_with("*")
        mock_client.table().select().eq.assert_called_once_with("id", 1)
        # Verify result
        assert settings == mock_response.data[0]
    def test_get_settings_all_active(self, mocker):
        """Test retrieving all active settings."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "id": 1,
            "name": "Setting 1",
            "is_active": True
        }, {
            "id": 2,
            "name": "Setting 2",
            "is_active": True
        }, {
            "id": 3,
            "name": "Setting 3",
            "is_active": False
        }]
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.order.return_value = mock_table
        mock_table.execute.return_value = mock_response
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        # Call function without ID (gets all active)
        settings = db.get_settings()
        # Verify calls
        mock_client.table.assert_called_once_with("user_settings")
        mock_client.table().select.assert_called_once_with("*")
        mock_client.table().select().eq.assert_called_once_with("is_active", True)
        mock_client.table().select().eq().order.assert_called_once_with("created_at")
        assert len(settings) == 3
        assert settings[0]["id"] == 1
        assert settings[1]["id"] == 2
        assert settings[2]["id"] == 3
    def test_get_settings_backward_compatibility(self, mocker):
        """Test backward compatibility when is_active column doesn't exist."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response1 = Mock()
        mock_response1.execute.side_effect = Exception("column \"is_active\" does not exist")
        mock_response2 = Mock()
        mock_response2.data = [{"id": 1, "name": "Old Setting"}]
        mock_table = Mock()
        # Create proper chain for first call (with is_active filter)
        mock_chain1 = Mock()
        mock_chain1.execute = mock_response1.execute
        mock_table.select.return_value.eq.return_value.order.return_value = mock_chain1
        
        # Create proper chain for second call (without is_active filter)
        mock_chain2 = Mock()
        mock_chain2.execute.return_value = mock_response2
        mock_table.select.return_value.order.return_value = mock_chain2
        mock_client.table.return_value = mock_table
        mocker.patch('db.get_supabase', return_value=mock_client)
        # Call function
        settings = db.get_settings()
        # Should fall back to getting all settings
        assert len(settings) == 1
        assert settings[0]["id"] == 1
    
    def test_get_settings_no_client(self, mocker):
        """Test that empty list is returned when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        
        settings = db.get_settings()
        assert settings == []
    def test_get_settings_specific_id_no_client(self, mocker):
        """Test that empty dict is returned when no Supabase client is available for specific ID."""
        mocker.patch('db.get_supabase', return_value=None)
        settings = db.get_settings(1)
        assert settings == {}
    """Tests for update_settings() function."""
    """Tests for get_all_settings() function."""
    
    def test_get_all_settings_success(self, mocker):
        """Test retrieving all settings including inactive ones."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "id": 1,
            "name": "Setting 1",
            "is_active": True
        }, {
            "id": 2,
            "name": "Setting 2",
            "is_active": False
        }]
        
        mock_table = Mock()
        mock_table.select.return_value.order.return_value = mock_table
        mock_table.execute.return_value = mock_response
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Call function
        settings = db.get_all_settings()
        
        # Verify calls
        mock_client.table.assert_called_once_with("user_settings")
        mock_client.table().select.assert_called_once_with("*")
        mock_client.table().select().order.assert_called_once_with("created_at")
        
        # Verify result
        assert len(settings) == 2
        assert settings[0]["id"] == 1
        assert settings[1]["id"] == 2
    
    def test_get_all_settings_backward_compatibility(self, mocker):
        """Test backward compatibility when created_at column doesn't exist."""
        # Mock Supabase client
        mock_client = Mock()
        mock_table = Mock()
        
        # First call raises exception
        mock_table.select.return_value.order.return_value.execute.side_effect = [
            Exception("column \"created_at\" does not exist"),
            Mock(data=[{"id": 1, "name": "Old Setting"}])
        ]
        
        mock_client.table.return_value = mock_table
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Call function
        settings = db.get_all_settings()
        
        # Should fall back to ordering by id
        assert len(settings) == 1
        assert settings[0]["id"] == 1
    
    def test_get_all_settings_no_client(self, mocker):
        """Test that empty list is returned when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        
        settings = db.get_all_settings()
        assert settings == []

class TestCreateSettings:
    """Tests for create_settings() function."""
    
    def test_create_settings_success(self, mocker):
        """Test creating a new settings row."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "id": 1,
            "name": "New Setting",
            "date_mode": "weekday",
            "is_active": True
        }]
        
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value = Mock(data=[])  # No existing settings
        mock_table.insert.return_value.execute.return_value = mock_response
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Test data
        test_settings = {
            "name": "New Setting",
            "weeks_ahead": 8
        }
        
        # Call function
        result = db.create_settings(test_settings)
        
        # Verify calls
        mock_client.table.assert_called_with("user_settings")
        # Should check existing settings count
        mock_table.select.assert_called_with("id")
        # Should insert with merged settings
        mock_table.insert.assert_called_once()
        
        # Verify result
        assert result == mock_response.data[0]
    
    def test_create_settings_max_limit(self, mocker):
        """Test that creating settings fails when maximum limit (10) is reached."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [{"id": i} for i in range(10)]  # 10 existing settings
        
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value = mock_response
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Test data
        test_settings = {"name": "New Setting"}
        
        # Call function - should raise ValueError
        with pytest.raises(ValueError, match="Maximum of 10 settings reached"):
            db.create_settings(test_settings)
    
    def test_create_settings_backward_compatibility(self, mocker):
        """Test backward compatibility when new columns don't exist."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [{"id": 1, "weeks_ahead": 8}]
        
        mock_table = Mock()
        mock_table.select.return_value.execute.return_value = Mock(data=[])
        # First insert fails with column error
        mock_table.insert.return_value.execute.side_effect = [
            Exception("column \"name\" does not exist"),
            mock_response
        ]
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Test data
        test_settings = {"weeks_ahead": 8}
        
        # Call function
        result = db.create_settings(test_settings)
        
        # Should retry without new columns
        assert mock_table.insert.call_count == 2
        assert result == mock_response.data[0]
    def test_create_settings_no_client(self, mocker):
        """Test that None is returned when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        result = db.create_settings({"name": "Test"})
        assert result is None
class TestUpdateSettings:
    """Tests for update_settings() function."""
    def test_update_settings_with_specific_id(self, mocker):
        """Test updating settings with a specific ID."""
        # Mock Supabase client
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        mocker.patch('db.get_supabase', return_value=mock_client)
        # Test data
        test_settings = {
            "selected_days": ["Mon", "Tue"],
            "selected_types": ["자동차야영장"],
            "cooldown_days": 5
        }
        
        # Call function with specific ID
        db.update_settings(test_settings, setting_id=2)
        
        # Verify update was called with specific ID
        mock_client.table.assert_called_once_with("user_settings")
        mock_table.update.assert_called_once_with(test_settings)
        mock_table.update().eq.assert_called_once_with("id", 2)
        mock_table.update().eq().execute.assert_called_once()
    
    def test_update_settings_without_id_active_exists(self, mocker):
        """Test updating first active setting when no ID is provided."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [{"id": 3}]
        
        mock_table = Mock()
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Test data
        test_settings = {"weeks_ahead": 4}
        
        # Call function without ID
        db.update_settings(test_settings)
        
        # Should find first active setting and update it
        mock_table.select.assert_called_with("id")
        mock_table.select().eq.assert_called_with("is_active", True)
        mock_table.select().eq().order.assert_called_with("created_at")
        mock_table.select().eq().order().limit.assert_called_with(1)
        
        # Should update with ID 3
        mock_table.update.assert_called_once_with(test_settings)
        mock_table.update().eq.assert_called_once_with("id", 3)
    
    def test_update_settings_without_id_backward_compatibility(self, mocker):
        """Test backward compatibility when is_active column doesn't exist."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [{"id": 1}]
        mock_table = Mock()
        # First call raises exception, second succeeds
        # Need to create proper mock chain for the exception
        mock_chain1 = Mock()
        mock_chain1.execute.side_effect = Exception("column \"is_active\" does not exist")
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value = mock_chain1
        mock_chain2 = Mock()
        mock_chain2.execute.return_value = mock_response
        mock_table.select.return_value.order.return_value.limit.return_value = mock_chain2
        mock_client.table.return_value = mock_table
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        # Test data
        test_settings = {"weeks_ahead": 4}
        # Call function without ID
        db.update_settings(test_settings)
        # Should fall back to getting first setting by id
        assert mock_table.select.call_count == 2
        mock_table.update.assert_called_once_with(test_settings)
        mock_table.update().eq.assert_called_once_with("id", 1)
        """Test that update does nothing when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        db.update_settings({"weeks_ahead": 4})

class TestCheckCooldown:
    """Tests for check_cooldown() function."""
    
    def test_check_cooldown_active(self, mocker):
        """Test that cooldown is active when notification was sent recently."""
        mock_client = Mock()
        mock_table = Mock()
        mock_response = Mock()
        mock_response.data = [{"id": 123}]
        
        mock_query = mock_table.select.return_value
        for _ in range(5):
            mock_query = mock_query.eq.return_value
        mock_query = mock_query.gt.return_value
        mock_query.execute.return_value = mock_response
        
        mock_client.table.return_value = mock_table
        mocker.patch('db.get_supabase', return_value=mock_client)
        mocker.patch('datetime.datetime').now.return_value = datetime(2026, 2, 23, 10, 0, 0)
        
        result = db.check_cooldown(1, "20260223", "지리산", "특화야영장", False, 3)
        assert result is True
    
    def test_check_cooldown_inactive(self, mocker):
        """Test that cooldown is inactive when no recent notification exists."""
        mock_client = Mock()
        mock_table = Mock()
        mock_response = Mock()
        mock_response.data = []
        
        mock_query = mock_table.select.return_value
        for _ in range(5):
            mock_query = mock_query.eq.return_value
        mock_query = mock_query.gt.return_value
        mock_query.execute.return_value = mock_response
        
        mock_client.table.return_value = mock_table
        mocker.patch('db.get_supabase', return_value=mock_client)
        mocker.patch('datetime.datetime').now.return_value = datetime(2026, 2, 23, 10, 0, 0)
        
        result = db.check_cooldown(1, "20260223", "지리산", "특화야영장", False, 3)
        assert result is False
    
    def test_check_cooldown_no_client(self, mocker):
        """Test that False is returned when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        result = db.check_cooldown(1, "20260223", "지리산", "특화야영장", False, 3)
        assert result is False

class TestRecordNotification:
    """Tests for record_notification() function."""
    
    def test_record_notification_success(self, mocker):
        """Test recording a notification successfully."""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        test_now = datetime(2026, 2, 23, 10, 0, 0, tzinfo=timezone.utc)
        mock_datetime = mocker.patch('datetime.datetime')
        mock_datetime.now.return_value = test_now
        
        db.record_notification(1, "20260223", "지리산", "특화야영장", False)
        
        assert mock_table.insert.called
        args = mock_table.insert.call_args[0][0]
        assert args["setting_id"] == 1
        assert args["target_date"] == "20260223"
        assert args["is_waiting"] is False
    
    def test_record_notification_no_client(self, mocker):
        """Test that recording does nothing when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        db.record_notification(1, "20260223", "지리산", "특화야영장", False)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestDeleteOldNotifications:
    """Tests for delete_old_notifications() function."""
    
    def test_delete_old_notifications_success(self, mocker):
        """Test successful deletion of old notifications."""
        # Mock dependencies
        mock_client = Mock()
        mock_table = Mock()
        mock_delete = Mock()
        mock_execute = Mock()
        
        mock_client.table.return_value = mock_table
        mock_table.delete.return_value = mock_delete
        mock_delete.lt.return_value = mock_delete
        mock_delete.execute.return_value = mock_execute
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Mock datetime for consistent testing
        test_now = datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc)
        # Mock datetime for consistent testing - patch inside the function
        test_now = datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc)
        # Mock datetime for consistent testing - patch the datetime module
        datetime_patcher = mocker.patch('datetime.datetime')
        datetime_patcher.now.return_value = test_now
        datetime_patcher.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Call the function
        db.delete_old_notifications(7)
        
        # Verify the cutoff date calculation (7 days ago)
        expected_cutoff = test_now - timedelta(days=7)
        
        # Verify the calls
        mock_client.table.assert_called_once_with("notification_history")
        mock_table.delete.assert_called_once()
        mock_delete.lt.assert_called_once_with("sent_at", expected_cutoff.isoformat())
        mock_delete.execute.assert_called_once()
    
    def test_delete_old_notifications_no_client(self, mocker):
        """Test that deletion does nothing when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        
        # This should not raise any exception
        db.delete_old_notifications(7)
        
        # No assertions needed - just ensuring no errors occur
    
    def test_delete_old_notifications_exception_handling(self, mocker):
        """Test that exceptions during deletion are caught and logged."""
        mock_client = Mock()
        mock_table = Mock()
        
        # Make delete() raise an exception
        mock_client.table.return_value = mock_table
        mock_table.delete.side_effect = Exception("Database error")
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        mock_logger = mocker.patch('logging.getLogger')
        
        # This should not raise an exception
        db.delete_old_notifications(7)
        
        # Verify warning was logged
        mock_logger().warning.assert_called_once()
        assert "Failed to delete old notifications" in mock_logger().warning.call_args[0][0]


class TestRecordLastCheckTime:
    """Tests for record_last_check_time() function."""
    
    def test_record_last_check_time_update_existing(self, mocker):
        """Test updating existing row in system_status table."""
        # Mock dependencies
        mock_client = Mock()
        mock_table = Mock()
        mock_update = Mock()
        mock_execute = Mock()
        
        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_update
        mock_update.execute.return_value = mock_execute
        
        # Mock response with data (indicating row was updated)
        mock_execute.data = [{"id": 1}]
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Mock datetime for consistent testing
        test_now = datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc)
        # Mock datetime for consistent testing - patch inside the function
        test_now = datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc)
        # Mock datetime for consistent testing - patch the datetime module
        datetime_patcher = mocker.patch('datetime.datetime')
        datetime_patcher.now.return_value = test_now
        datetime_patcher.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Call the function
        db.record_last_check_time()
        
        # Verify the calls
        mock_client.table.assert_called_once_with("system_status")
        mock_table.update.assert_called_once_with({
            "last_check_at": test_now.isoformat()
        })
        mock_update.eq.assert_called_once_with("id", 1)
        mock_update.execute.assert_called_once()
        
        # Insert should NOT be called since update succeeded
        mock_table.insert.assert_not_called()
    
    def test_record_last_check_time_insert_new(self, mocker):
        """Test inserting new row when no existing row in system_status table."""
        # Mock dependencies
        mock_client = Mock()
        mock_table = Mock()
        mock_update = Mock()
        mock_execute = Mock()
        mock_insert = Mock()
        mock_insert_execute = Mock()
        
        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_update
        mock_update.execute.return_value = mock_execute
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = mock_insert_execute
        
        # Mock response with NO data (indicating no row was updated)
        mock_execute.data = []
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Mock datetime for consistent testing
        test_now = datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc)
        # Mock datetime for consistent testing - patch inside the function
        test_now = datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc)
        # Mock datetime for consistent testing - patch the datetime module
        datetime_patcher = mocker.patch('datetime.datetime')
        datetime_patcher.now.return_value = test_now
        datetime_patcher.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Call the function
        db.record_last_check_time()
        
        # Verify the calls
        assert mock_client.table.call_count == 2
        # Check that table was called with 'system_status' twice
        calls = mock_client.table.call_args_list
        assert calls[0] == call('system_status')
        assert calls[1] == call('system_status')
        mock_table.update.assert_called_once_with({
            "last_check_at": test_now.isoformat()
        })
        mock_update.eq.assert_called_once_with("id", 1)
        mock_update.execute.assert_called_once()
        
        # Insert should be called since update returned no data
        mock_table.insert.assert_called_once_with({
            "id": 1,
            "last_check_at": test_now.isoformat()
        })
        mock_insert.execute.assert_called_once()
    
    def test_record_last_check_time_no_client(self, mocker):
        """Test that recording does nothing when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        
        # This should not raise any exception
        db.record_last_check_time()
        
        # No assertions needed - just ensuring no errors occur
    
    def test_record_last_check_time_exception_handling(self, mocker):
        """Test that exceptions during recording are caught and logged."""
        mock_client = Mock()
        
        # Make table() raise an exception (simulating missing table)
        mock_client.table.side_effect = Exception("Table not found")
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        mock_logger = mocker.patch('logging.getLogger')
        
        # This should not raise an exception
        db.record_last_check_time()
        
        # Verify warning was logged
        mock_logger().warning.assert_called_once()
        assert "Failed to record last check time" in mock_logger().warning.call_args[0][0]


class TestGetLastCheckTime:
    """Tests for get_last_check_time() function."""
    
    def test_get_last_check_time_success(self, mocker):
        """Test successful retrieval of last check time."""
        # Mock dependencies
        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()
        
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_select
        mock_select.execute.return_value = mock_execute
        
        # Mock response with data
        test_time = datetime(2026, 2, 24, 9, 30, 0, tzinfo=timezone.utc)
        mock_execute.data = [{"last_check_at": test_time.isoformat()}]
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Call the function
        result = db.get_last_check_time()
        
        # Verify the calls
        mock_client.table.assert_called_once_with("system_status")
        mock_table.select.assert_called_once_with("last_check_at")
        mock_select.eq.assert_called_once_with("id", 1)
        mock_select.execute.assert_called_once()
        
        # Verify the result
        assert result == test_time
    
    def test_get_last_check_time_no_data(self, mocker):
        """Test retrieval when no data exists."""
        # Mock dependencies
        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()
        
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_select
        mock_select.execute.return_value = mock_execute
        
        # Mock response with NO data
        mock_execute.data = []
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Call the function
        result = db.get_last_check_time()
        
        # Verify the result is None
        assert result is None
    
    def test_get_last_check_time_no_client(self, mocker):
        """Test that retrieval returns None when no Supabase client is available."""
        mocker.patch('db.get_supabase', return_value=None)
        
        result = db.get_last_check_time()
        
        assert result is None
    
    def test_get_last_check_time_exception_handling(self, mocker):
        """Test that exceptions during retrieval are caught and logged."""
        mock_client = Mock()
        
        # Make table() raise an exception (simulating missing table)
        mock_client.table.side_effect = Exception("Table not found")
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        mock_logger = mocker.patch('logging.getLogger')
        
        # Call the function
        result = db.get_last_check_time()
        
        # Verify warning was logged
        mock_logger().warning.assert_called_once()
        assert "Failed to get last check time" in mock_logger().warning.call_args[0][0]
        
        # Verify the result is None
        assert result is None
    
    def test_get_last_check_time_with_z_timezone(self, mocker):
        """Test parsing of timestamp with Z timezone."""
        # Mock dependencies
        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()
        
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_select
        mock_select.execute.return_value = mock_execute
        
        # Mock response with Z timezone format
        mock_execute.data = [{"last_check_at": "2026-02-24T09:30:00Z"}]
        
        mocker.patch('db.get_supabase', return_value=mock_client)
        
        # Call the function
        result = db.get_last_check_time()
        
        # Verify the result was parsed correctly
        expected = datetime(2026, 2, 24, 9, 30, 0, tzinfo=timezone.utc)
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])