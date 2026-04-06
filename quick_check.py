#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('smartguard.db')
c = conn.cursor()

print("🔍 Checking mahernada562@gmail.com...")
c.execute('SELECT email, password_hash FROM users WHERE email = ?', ('mahernada562@gmail.com',))
user = c.fetchone()

if user:
    print(f"✅ User found:")
    print(f"   Email: {user[0]}")
    print(f"   Password Hash: {user[1]}")
    print(f"   Starts with RESET_REQUIRED: {user[1].startswith('RESET_REQUIRED')}")
else:
    print("❌ User not found")

print("\n🔍 Checking all users with RESET_REQUIRED...")
c.execute('SELECT email, password_hash FROM users WHERE password_hash LIKE ?', ('RESET_REQUIRED%',))
users = c.fetchall()

print(f"Found {len(users)} users with RESET_REQUIRED:")
for email, pwd_hash in users:
    print(f"   - {email}")

conn.close()
