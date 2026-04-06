#!/usr/bin/env python3
"""
Debug script to test correct password authentication
"""
import sqlite3
import sys
sys.path.append(".")

from routers.auth import hash_password, verify_password

def test_correct_password():
    """Test what happens when correct password is used"""
    
    print("🔍 Testing Correct Password Scenario")
    print("=" * 50)
    
    # Test user setup
    conn = sqlite3.connect('smartguard.db')
    c = conn.cursor()
    
    try:
        email = "ahmedsaad33@gmail.com"
        correct_password = "tempsecure123"
        
        # Get current user data
        c.execute('SELECT email, password_hash, status FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        
        if not user:
            print(f"❌ User {email} not found")
            return
        
        email, password_hash, status = user
        print(f"✅ User found: {email}")
        print(f"   Status: {status}")
        print(f"   Current hash: {password_hash[:50]}...")
        print(f"   Is RESET_REQUIRED: {password_hash.startswith('RESET_REQUIRED')}")
        
        # Ensure user has proper password hash
        if password_hash.startswith('RESET_REQUIRED'):
            print(f"🔧 Setting proper password...")
            proper_hash = hash_password(correct_password)
            c.execute('UPDATE users SET password_hash = ? WHERE email = ?', (proper_hash, email))
            conn.commit()
            password_hash = proper_hash
            print(f"✅ Password set to: {correct_password}")
            print(f"   New hash: {password_hash[:50]}...")
        
        # Test password verification
        print(f"\n🧪 Testing password verification:")
        print(f"   Testing password: {correct_password}")
        print(f"   Against hash: {password_hash[:50]}...")
        
        # Test the actual verification function
        result = verify_password(correct_password, password_hash)
        print(f"   Verification result: {result}")
        
        if result:
            print(f"   ✅ SUCCESS: Correct password verified")
        else:
            print(f"   ❌ FAILED: Correct password not verified")
            
            # Debug the verification process
            print(f"\n🔍 Debugging verification:")
            try:
                salt, hash_part = password_hash.split('$')
                print(f"   Salt: {salt}")
                print(f"   Hash part: {hash_part}")
                print(f"   Password: {correct_password}")
                
                # Manual hash calculation
                import hashlib
                manual_hash = hashlib.pbkdf2_hmac('sha256', correct_password.encode(), salt.encode(), 100000).hex()
                print(f"   Manual hash: {manual_hash}")
                print(f"   Expected hash: {hash_part}")
                print(f"   Hashes match: {manual_hash == hash_part}")
                
            except Exception as e:
                print(f"   ❌ Debug error: {e}")
        
        # Simulate the full authentication flow
        print(f"\n🎭 Simulating full authentication flow:")
        print(f"   1. User found: ✅")
        print(f"   2. Status check: {status}")
        
        if status != 'approved':
            print(f"   3. Status check: ❌ (not approved)")
            print(f"   Should reject: YES")
        else:
            print(f"   3. Status check: ✅ (approved)")
        
        print(f"   4. Password verification: {result}")
        print(f"   5. Should allow login: {result and status == 'approved'}")
        
        if result and status == 'approved':
            print(f"   🎉 SUCCESS: Login should be allowed")
        else:
            print(f"   ❌ FAILED: Login should be rejected")
        
        # Test the actual signin logic
        print(f"\n📝 Testing signin logic:")
        
        # Import the signin logic
        from routers.auth import SigninRequest
        
        # Create a mock request
        class MockRequest:
            def __init__(self, email, password):
                self.email = email
                self.password = password
        
        mock_request = MockRequest(email, correct_password)
        
        # Test the password verification part
        if password_hash.startswith("RESET_REQUIRED"):
            print(f"   RESET_REQUIRED path: {len(correct_password) >= 6}")
            if len(correct_password) >= 6:
                print(f"   Would set new password and allow login")
            else:
                print(f"   Would reject (too short)")
        else:
            print(f"   Normal verification path: {verify_password(correct_password, password_hash)}")
            if verify_password(correct_password, password_hash):
                print(f"   Would allow login")
            else:
                print(f"   Would reject login")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_correct_password()
