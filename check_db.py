import sqlite3
import json

def check_db():
    conn = sqlite3.connect("smartguard.db")
    c = conn.cursor()
    
    print("--- Signup Requests ---")
    c.execute("SELECT id, email, full_name, organization, role, status FROM signup_requests")
    rows = c.fetchall()
    for row in rows:
        print(row)
        
    print("\n--- Users ---")
    c.execute("SELECT id, email, full_name, organization, role, status FROM users")
    rows = c.fetchall()
    for row in rows:
        print(row)
    
    conn.close()

if __name__ == "__main__":
    check_db()
