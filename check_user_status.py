#!/usr/bin/env python3
"""
Check user approval status for ahmedsaad33@gmail.com
"""
import sqlite3

def check_user_status():
    """Check if ahmedsaad33@gmail.com is approved"""
    
    print("🔍 Checking User Approval Status")
    print("=" * 40)
    
    conn = sqlite3.connect('smartguard.db')
    c = conn.cursor()
    
    try:
        email = "ahmedsaad33@gmail.com"
        
        # Get user data
        c.execute('SELECT email, full_name, password_hash, organization, role, status FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        
        if not user:
            print(f"❌ User {email} not found")
            return
        
        email, full_name, password_hash, organization, role, status = user
        print(f"✅ User found: {email}")
        print(f"   Full Name: {full_name}")
        print(f"   Organization: {organization}")
        print(f"   Role: {role}")
        print(f"   Status: {status}")
        print(f"   Password Hash: {password_hash[:50]}...")
        print(f"   Is RESET_REQUIRED: {password_hash.startswith('RESET_REQUIRED')}")
        
        # Check if user is approved
        if status == 'approved':
            print(f"   ✅ User is APPROVED - can login")
        else:
            print(f"   ❌ User is NOT approved - status: {status}")
            print(f"   🚫 This is why login fails even with correct password")
        
        # Fix status if needed
        if status != 'approved':
            print(f"\n🔧 Fixing user status to 'approved'...")
            c.execute('UPDATE users SET status = ? WHERE email = ?', ('approved', email))
            conn.commit()
            print(f"✅ User {email} is now approved")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_user_status()
