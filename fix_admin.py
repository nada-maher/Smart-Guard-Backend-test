import sqlite3
import hashlib
import secrets

# Connect to database
conn = sqlite3.connect('smartguard.db')
c = conn.cursor()

# Delete old admin if exists
c.execute('DELETE FROM users WHERE email = ?', ('admin@smartguard.com',))

# Hash password correctly
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt + '$' + password_hash.hex()

# Create new admin with correct hash
admin_id = secrets.token_urlsafe(16)
admin_email = 'admin@smartguard.com'
admin_password = 'admin123456'
admin_org = 'Smart Guard'
admin_role = 'admin'
password_hash = hash_password(admin_password)

c.execute('''INSERT INTO users (id, email, full_name, password_hash, organization, role, status)
VALUES (?, ?, ?, ?, ?, ?, ?)''', 
(admin_id, admin_email, 'System Admin', password_hash, admin_org, admin_role, 'approved'))
conn.commit()
conn.close()

print('✅ Admin account created successfully!')
print('Email: admin@smartguard.com')
print('Password: admin123456')
print('Organization: Smart Guard')
