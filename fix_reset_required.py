#!/usr/bin/env python3
"""
Fix all users with RESET_REQUIRED password hashes to prevent any password login
"""
import sqlite3
import sys
sys.path.append(".")

from routers.auth import hash_password

def fix_reset_required_users():
    """Fix all users with RESET_REQUIRED password hashes"""
    
    print("🔧 Fixing all users with RESET_REQUIRED password hashes...")
    
    conn = sqlite3.connect('smartguard.db')
    c = conn.cursor()
    
    try:
        # Find all users with RESET_REQUIRED
        c.execute('SELECT email, full_name FROM users WHERE password_hash LIKE ?', ('RESET_REQUIRED%',))
        users = c.fetchall()
        
        if not users:
            print("✅ No users with RESET_REQUIRED password hash found")
            return
        
        print(f"🚨 Found {len(users)} users with RESET_REQUIRED password hash:")
        for email, full_name in users:
            print(f"   - {email} ({full_name})")
        
        print(f"\n🔧 Fixing all users...")
        fixed_count = 0
        
        for email, full_name in users:
            # Generate a proper password hash
            temp_password = "tempsecure123"
            proper_hash = hash_password(temp_password)
            
            # Update the user
            c.execute('UPDATE users SET password_hash = ? WHERE email = ?', (proper_hash, email))
            fixed_count += 1
            print(f"   ✅ Fixed: {email} - Temporary password: {temp_password}")
        
        conn.commit()
        print(f"\n✅ Successfully fixed {fixed_count} users!")
        print(f"🔐 All users now have proper password hashes")
        print(f"📝 Temporary password for all fixed users: tempsecure123")
        
        # Verify the fix
        c.execute('SELECT email, password_hash FROM users WHERE password_hash LIKE ?', ('RESET_REQUIRED%',))
        remaining = c.fetchall()
        
        if remaining:
            print(f"\n❌ Still have {len(remaining)} users with RESET_REQUIRED:")
            for email, pwd_hash in remaining:
                print(f"   - {email}")
        else:
            print(f"\n✅ All users successfully fixed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def verify_fix():
    """Verify that the fix worked by testing authentication"""
    
    print(f"\n🧪 Verifying the fix...")
    
    conn = sqlite3.connect('smartguard.db')
    c = conn.cursor()
    
    try:
        # Test mahernada562@gmail.com specifically
        c.execute('SELECT email, password_hash FROM users WHERE email = ?', ('mahernada562@gmail.com',))
        user = c.fetchone()
        
        if user:
            email, password_hash = user[0], user[1]
            print(f"✅ User {email} found:")
            print(f"   Password hash: {password_hash[:50]}...")
            print(f"   Is RESET_REQUIRED: {password_hash.startswith('RESET_REQUIRED')}")
            
            # Test password verification
            from routers.auth import verify_password
            
            test_passwords = ["wrongpass", "123", "anypassword", "tempsecure123"]
            print(f"\n🧪 Testing password verification:")
            
            for test_pwd in test_passwords:
                result = verify_password(test_pwd, password_hash)
                print(f"   Password '{test_pwd}': {'✅ ACCEPTED' if result else '❌ REJECTED'}")
        else:
            print(f"❌ User mahernada562@gmail.com not found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔐 Smart Guard Security Fix")
    print("=" * 40)
    
    fix_reset_required_users()
    verify_fix()
    
    print(f"\n🎯 Next Steps:")
    print(f"1. Restart the backend server")
    print(f"2. Try logging in with mahernada562@gmail.com")
    print(f"3. Use password: tempsecure123")
    print(f"4. Verify that wrong passwords are rejected")
    print(f"5. Change password after successful login")
