#!/usr/bin/env python3
"""
Debug script to check specific user authentication issue
"""
import sqlite3
import sys
import os
sys.path.append(".")

from routers.auth import hash_password, verify_password

def debug_user_auth():
    """Debug authentication for mahernada562@gmail.com"""
    
    email = "mahernada562@gmail.com"
    print(f"🔍 Debugging authentication for: {email}")
    
    # Connect to database
    conn = sqlite3.connect('smartguard.db')
    c = conn.cursor()
    
    try:
        # Check user in local database
        c.execute("SELECT id, email, full_name, password_hash, organization, role, status FROM users WHERE email = ?", (email,))
        user_data = c.fetchone()
        
        if user_data:
            user_id, email, full_name, password_hash, organization, role, status = user_data
            print(f"✅ User found in local database:")
            print(f"   ID: {user_id}")
            print(f"   Email: {email}")
            print(f"   Name: {full_name}")
            print(f"   Password Hash: {password_hash}")
            print(f"   Organization: {organization}")
            print(f"   Role: {role}")
            print(f"   Status: {status}")
            print(f"   Is RESET_REQUIRED: {password_hash.startswith('RESET_REQUIRED') if password_hash else 'N/A'}")
            
            # Test password verification
            test_passwords = ["123456", "wrongpassword", "anypassword", "correctpass"]
            
            print(f"\n🧪 Testing password verification:")
            for test_pwd in test_passwords:
                if password_hash.startswith("RESET_REQUIRED"):
                    # This is the issue - any password will be accepted!
                    result = len(test_pwd) >= 6  # Current logic
                    print(f"   Password '{test_pwd}': {'✅ ACCEPTED' if result else '❌ REJECTED (too short)'}")
                else:
                    result = verify_password(test_pwd, password_hash)
                    print(f"   Password '{test_pwd}': {'✅ ACCEPTED' if result else '❌ REJECTED'}")
            
            # Show the security vulnerability
            if password_hash.startswith("RESET_REQUIRED"):
                print(f"\n🚨 SECURITY VULNERABILITY DETECTED!")
                print(f"   User has 'RESET_REQUIRED' password hash")
                print(f"   This means ANY 6+ character password will be accepted")
                print(f"   This is the bypass allowing login with any password")
                
                # Fix it by setting a proper password hash
                print(f"\n🔧 Fixing the security issue...")
                proper_hash = hash_password("temppassword123")
                c.execute("UPDATE users SET password_hash = ? WHERE email = ?", (proper_hash, email))
                conn.commit()
                print(f"✅ Fixed! User now has proper password hash")
                print(f"   Temporary password: temppassword123")
                
        else:
            print(f"❌ User {email} NOT found in local database")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

def check_all_reset_required_users():
    """Check all users with RESET_REQUIRED password hash"""
    
    print(f"\n🔍 Checking all users with RESET_REQUIRED password hash...")
    
    conn = sqlite3.connect('smartguard.db')
    c = conn.cursor()
    
    try:
        c.execute("SELECT email, full_name, password_hash FROM users WHERE password_hash LIKE 'RESET_REQUIRED%'")
        users = c.fetchall()
        
        if users:
            print(f"🚨 Found {len(users)} users with RESET_REQUIRED password hash:")
            for email, full_name, password_hash in users:
                print(f"   - {email} ({full_name})")
            
            print(f"\n🔧 Fixing all users...")
            for email, full_name, password_hash in users:
                proper_hash = hash_password("temppassword123")
                c.execute("UPDATE users SET password_hash = ? WHERE email = ?", (proper_hash, email))
                print(f"   ✅ Fixed: {email}")
            
            conn.commit()
            print(f"✅ All users fixed! Temporary password: temppassword123")
        else:
            print(f"✅ No users with RESET_REQUIRED password hash found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔐 Smart Guard User Authentication Debug")
    print("=" * 50)
    
    debug_user_auth()
    check_all_reset_required_users()
    
    print(f"\n🎯 Next Steps:")
    print(f"1. Try logging in with email: mahernada562@gmail.com")
    print(f"2. Use temporary password: temppassword123")
    print(f"3. Change password immediately after login")
    print(f"4. Test that wrong passwords are now rejected")
