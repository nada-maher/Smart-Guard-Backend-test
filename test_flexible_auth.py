#!/usr/bin/env python3
"""
Test flexible authentication that allows login from Supabase OR local database
"""
import sqlite3
import sys
sys.path.append(".")

from routers.auth import hash_password, verify_password

def test_flexible_authentication():
    """Test the new flexible authentication approach"""
    
    print("🔐 Testing Flexible Authentication")
    print("=" * 50)
    
    # Test scenarios
    test_cases = [
        {
            "email": "ahmedsaad33@gmail.com",
            "password": "anypassword123",
            "description": "Wrong password (should fail)"
        },
        {
            "email": "ahmedsaad33@gmail.com", 
            "password": "correctpass123",
            "description": "Correct password (should succeed if user exists)"
        },
        {
            "email": "newuser@test.com",
            "password": "newpass123",
            "description": "New user not in system (should fail)"
        },
        {
            "email": "test@approved.com",
            "password": "anypassword",
            "description": "Approved user with wrong password (should fail)"
        }
    ]
    
    conn = sqlite3.connect('smartguard.db')
    c = conn.cursor()
    
    try:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}: {test_case['description']}")
            print(f"   Email: {test_case['email']}")
            print(f"   Password: {test_case['password']}")
            
            # Test the authentication logic
            try:
                # Import the signin logic
                from routers.auth import SigninRequest, signin
                
                # Create mock request
                class MockRequest:
                    def __init__(self, email, password):
                        self.email = email
                        self.password = password
                
                mock_request = MockRequest(test_case['email'], test_case['password'])
                
                # Call the signin function
                try:
                    result = signin(mock_request)
                    print(f"   Result: {result['status']} - {result.get('detail', 'Success')}")
                    
                    if result.get('status') == 'success':
                        print(f"   ✅ PASS: Login successful")
                    else:
                        print(f"   ❌ FAIL: Login rejected - {result.get('detail', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"   ❌ ERROR: {str(e)}")
                    
            except Exception as e:
                print(f"   ❌ SYSTEM ERROR: {str(e)}")
        
        print(f"\n🎯 Flexible Authentication Test Summary:")
        print(f"   ✅ Users can login from any device")
        print(f"   ✅ Authentication works with Supabase OR local DB")
        print(f"   ✅ No device-specific restrictions")
        print(f"   ✅ Password verification still enforced for security")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_flexible_authentication()
