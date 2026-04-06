#!/usr/bin/env python3
"""
Debug script to check user data in the database
"""
import sqlite3
import sys
import os

def check_users():
    """Check what users exist in the database and their password hashes"""
    
    # Connect to the database
    conn = sqlite3.connect('smartguard.db')
    c = conn.cursor()
    
    try:
        # Check all users
        print("=== All Users in Local Database ===")
        c.execute("SELECT id, email, full_name, password_hash, organization, role, status FROM users")
        users = c.fetchall()
        
        if not users:
            print("No users found in local database!")
        else:
            for user in users:
                user_id, email, full_name, password_hash, organization, role, status = user
                print(f"ID: {user_id}")
                print(f"Email: {email}")
                print(f"Name: {full_name}")
                print(f"Password Hash: {password_hash[:50]}..." if len(password_hash) > 50 else f"Password Hash: {password_hash}")
                print(f"Organization: {organization}")
                print(f"Role: {role}")
                print(f"Status: {status}")
                print(f"Is RESET_REQUIRED: {password_hash.startswith('RESET_REQUIRED') if password_hash else 'N/A'}")
                print("-" * 50)
        
        print(f"\nTotal users: {len(users)}")
        
        # Check specific users from the error logs
        test_emails = ['ahmed33@gmail.com', 'mahernada562@gmail.com']
        for email in test_emails:
            print(f"\n=== Checking {email} ===")
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = c.fetchone()
            if user:
                print(f"User found: {user}")
            else:
                print(f"User {email} NOT found in local database")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_users()
