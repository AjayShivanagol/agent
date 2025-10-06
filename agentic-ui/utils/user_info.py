import base64
import json
from typing import Dict, Optional

def decode_userinfo(userinfo_header: Optional[str]) -> Dict:
    """
    Decode the base64-encoded x-userinfo header into a dictionary.
    
    Args:
        userinfo_header: Base64-encoded string containing user information
        
    Returns:
        Dictionary containing decoded user information
        
    Example:
        >>> decode_userinfo("eyJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJpZCI6IlVTRVJJRCJ9")
        {'email': 'user@example.com', 'id': 'USERID'}
    """
    if not userinfo_header:
        return {}  # No header provided
    
    try:
        # Fix base64 padding if needed
        missing_padding = len(userinfo_header) % 4
        if missing_padding:
            userinfo_header += '=' * (4 - missing_padding)
        
        # Decode base64 string
        decoded_bytes = base64.b64decode(userinfo_header)
        decoded_str = decoded_bytes.decode('utf-8')
        
        # Parse JSON
        user_info = json.loads(decoded_str)
        return user_info
    except Exception as e:
        print(f"Error decoding userinfo: {e}")
        return {}  # Return empty on error
        
def get_user_id(userinfo_header: Optional[str]) -> str:
    """
    Extract the user ID from the userinfo header.
    
    Args:
        userinfo_header: Base64-encoded string containing user information
        
    Returns:
        User ID string or empty string if missing
    """
    user_info = decode_userinfo(userinfo_header)
    return user_info.get('id', '')

def encode_userinfo(user_info: Dict) -> str:
    """
    Encode user information into a base64 string for use in the x-userinfo header.
    
    Args:
        user_info: Dictionary containing user information including user_id
        
    Returns:
        Base64-encoded string
        
    Example:
        >>> encode_userinfo({'user_id': 'user1', 'email': 'user1@example.com'})
        'eyJ1c2VyX2lkIjoidXNlcjEiLCJlbWFpbCI6InVzZXIxQGV4YW1wbGUuY29tIn0='
    """
    try:
        # Convert dictionary to JSON string
        json_str = json.dumps(user_info)
        
        # Encode to bytes and then base64
        encoded_bytes = base64.b64encode(json_str.encode('utf-8'))
        
        # Convert bytes to string for header
        return encoded_bytes.decode('utf-8')
    except Exception as e:
        print(f"Error encoding userinfo: {e}")
        return ""
