import base64
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the parent directory to the Python path to import the application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.user_info import decode_userinfo, get_user_id
from service.server.adk_host_manager import ADKHostManager
from service.server.server import ConversationServer


class TestUserSpecificConversations(unittest.TestCase):

    def setUp(self):
        # Create mock objects
        self.mock_http_client = MagicMock()
        self.mock_fastapi = MagicMock()

    def test_decode_userinfo(self):
        # Test with a valid header
        test_data = {"id": "AJSHIVA", "email": "test@example.com"}
        encoded_header = base64.b64encode(json.dumps(test_data).encode()).decode()
        
        # Test decoding
        result = decode_userinfo(encoded_header)
        self.assertEqual(result, test_data)
        
        # Test get_user_id
        user_id = get_user_id(encoded_header)
        self.assertEqual(user_id, "AJSHIVA")
        
        # Test with None header
        default_result = decode_userinfo(None)
        self.assertEqual(default_result["id"], "test_user")
        
        # Test with invalid header
        invalid_result = decode_userinfo("invalid-base64-data")
        self.assertEqual(invalid_result["id"], "test_user")

    @patch('service.server.adk_host_manager.ADKHostManager._load_conversations_from_disk')
    @patch('service.server.adk_host_manager.ADKHostManager._save_conversations_to_disk')
    def test_adk_host_manager_user_specific_files(self, mock_save, mock_load):
        # Test that the conversations file path includes user ID
        manager1 = ADKHostManager(self.mock_http_client, user_id="user1")
        manager2 = ADKHostManager(self.mock_http_client, user_id="user2")
        
        # Check that different file paths are used for different users
        self.assertIn("conversation-user1.json", manager1._conversations_file_path())
        self.assertIn("conversation-user2.json", manager2._conversations_file_path())
        self.assertNotEqual(
            manager1._conversations_file_path(), 
            manager2._conversations_file_path()
        )

    @patch('fastapi.Request')
    @patch('service.server.ConversationServer.manager', new_callable=MagicMock)
    def test_conversation_server_userinfo_handling(self, mock_manager, mock_request):
        # Create test data
        test_userinfo = {"id": "test_user_123", "email": "test@example.com"}
        encoded_userinfo = base64.b64encode(json.dumps(test_userinfo).encode()).decode()
        
        # Setup request mock with header
        mock_request.headers = {"x-userinfo": encoded_userinfo}
        mock_request.json.return_value = {"params": "test-conversation-id"}
        
        # Create server instance and replace its manager with our mock
        server = ConversationServer(self.mock_fastapi, self.mock_http_client)
        
        # Create an ADKHostManager mock that will be cast to check type
        mock_adkhostmanager = MagicMock(spec=ADKHostManager)
        server.manager = mock_adkhostmanager
        
        # Call the method being tested
        server._list_conversation(mock_request)
        
        # Check that the user_id was updated correctly
        self.assertEqual(mock_adkhostmanager.user_id, "test_user_123")


if __name__ == "__main__":
    unittest.main()
