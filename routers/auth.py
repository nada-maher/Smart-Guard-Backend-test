"""
Authentication Router
Handles user registration, login, and user management with Supabase Integration
"""
from fastapi import APIRouter, HTTPException, Depends, status, Header
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import hashlib
import secrets
import json
import base64
from datetime import datetime
import sys
import os
from supabase import create_client, Client

sys.path.append("..")
from services.email_service import send_signup_notification_dev as send_signup_notification
from config.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Supabase initialization
# Use Service Role Key for admin operations (like deleting users)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

# Database setup (Keeping local SQLite as cache/backup)
def init_db():
    """Initialize database with users and signup requests tables"""
    conn = sqlite3.connect("smartguard.db")
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            organization TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'security_man',
            status TEXT NOT NULL DEFAULT 'approved',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Signup requests table (for pending approvals)
    c.execute('''
        CREATE TABLE IF NOT EXISTS signup_requests (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            organization TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'security_man',
            status TEXT NOT NULL DEFAULT 'pending',
            decline_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Pydantic Models
class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    organization: str
    role: str = "security_man"  # 'security_man' or 'admin'

class SigninRequest(BaseModel):
    email: str
    password: str

class DeclineRequest(BaseModel):
    reason: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

# Helpers
def hash_password(password: str) -> str:
    """Hash a password for storing"""
    salt = secrets.token_hex(8)
    hash_part = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${hash_part}"

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a stored password against one provided by user"""
    try:
        salt, hash_part = password_hash.split('$')
        password_check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return password_check.hex() == hash_part
    except:
        return False

def generate_token(user_id: str, email: str, organization: str, role: str) -> str:
    """Generate token with user info encoded"""
    token_data = {
            "user_id": user_id,
            "email": email,
            "organization": organization,
            "role": role
        }
    token_json = json.dumps(token_data)
    token = base64.b64encode(token_json.encode()).decode()
    return token

def decode_token(token: str) -> dict:
    """Decode token to get user info"""
    try:
        print(f"DEBUG: Decoding token: {token[:20]}...")
        token_json = base64.b64decode(token.encode()).decode()
        data = json.loads(token_json)
        print(f"DEBUG: Decoded data: {data}")
        return data
    except Exception as e:
        print(f"DEBUG: Token decode error: {e}")
        return None

def get_db():
    """Get database connection"""
    return sqlite3.connect("smartguard.db")

# Endpoints
@router.post("/signup")
async def signup(request: SignupRequest):
    """Register a new user - Supabase is the primary source of truth for existence"""
    init_db()
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 1. MANDATORY: Check Supabase for existing account
        try:
            sb_response = supabase.table("users").select("*").eq("email", request.email).execute()
            if sb_response.data and len(sb_response.data) > 0:
                user = sb_response.data[0]
                status = user.get("status", "pending")
                
                if status == "pending":
                    raise HTTPException(status_code=400, detail="⚠️ هذا البريد الإلكتروني مسجل بالفعل كطلب معلق. يرجى انتظار موافقة المسؤول")
                elif status == "approved":
                    raise HTTPException(status_code=400, detail="⚠️ هذا البريد الإلكتروني مسجل بالفعل. يرجى استخدام بريد إلكتروني آخر أو تسجيل الدخول")
                elif status == "declined":
                    # Allow re-signup by deleting the declined record first
                    supabase.table("users").delete().eq("email", request.email).execute()
                    print(f"✅ Removed declined user {request.email} from Supabase for re-signup")
        except HTTPException as he:
            raise he
        except Exception as se:
            print(f"❌ Supabase check failed during signup: {se}")
            # If Supabase is unreachable, we can't safely allow signup
            raise HTTPException(status_code=503, detail="⚠️ فشل الاتصال بقاعدة البيانات. يرجى المحاولة لاحقاً")

        # 2. Cleanup local DB if it's out of sync with Supabase
        # (e.g. user was deleted from Supabase but still exists locally)
        c.execute("DELETE FROM users WHERE email = ?", (request.email,))
        c.execute("DELETE FROM signup_requests WHERE email = ?", (request.email,))
        conn.commit()
        
        # 3. Create new signup request
        request_id = secrets.token_urlsafe(16)
        password_hash = hash_password(request.password)
        
        c.execute('''
            INSERT INTO signup_requests (id, email, full_name, password_hash, organization, role, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (request_id, request.email, request.full_name, password_hash, request.organization, request.role))
        
        conn.commit()
        
        # 4. Sync to Supabase as pending
        data = {
            "email": request.email,
            "full_name": request.full_name,
            "organization": request.organization,
            "role": request.role,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        try:
            # Try to insert with custom ID
            insert_data = data.copy()
            insert_data["id"] = request_id
            supabase.table("users").insert(insert_data).execute()
            print(f"✅ Synced {request.email} to Supabase as pending")
        except:
            # Fallback to auto-ID if custom ID fails
            supabase.table("users").insert(data).execute()
            print(f"✅ Synced {request.email} to Supabase as pending (Auto-ID)")
        
        return {
            "message": "تم إرسال طلب التسجيل بنجاح. يرجى انتظار موافقة المسؤول",
            "status": "pending"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/signin")
async def signin(request: SigninRequest):
    """Sign in user - Flexible authentication allowing login from any device
    User can authenticate if they exist in Supabase OR local database"""
    print(f"🔐 === SIGNIN ATTEMPT ===")
    print(f"📧 Email: {request.email}")
    print(f"📧 Password: {'*' * len(request.password)} ({len(request.password)} chars)")
    print(f"🕐 Timestamp: {datetime.now().isoformat()}")
    
    init_db()
    conn = get_db()
    c = conn.cursor()
    try:
        # Try Supabase FIRST (primary source)
        print(f"🔍 Step 1: Checking Supabase for {request.email}")
        try:
            sb_response = supabase.table("users").select("*").eq("email", request.email).execute()
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            raise HTTPException(status_code=500, detail="فشل الاتصال بقاعدة البيانات")
        
        if sb_response.data and len(sb_response.data) > 0:
            print(f"✅ User {request.email} found in Supabase")
            sb_user = sb_response.data[0]
            sb_email = sb_user.get("email", request.email)
            sb_full_name = sb_user.get("full_name", "")
            sb_organization = sb_user.get("organization", "")
            sb_role = sb_user.get("role", "security_man")
            sb_status = sb_user.get("status", "pending")
            
            # Check if user is approved in Supabase
            if sb_status == 'approved':
                print(f"✅ User is approved in Supabase - allowing login")
                
                # For Supabase users, we need to handle password differently
                # Since Supabase doesn't store passwords, we need to verify against local DB
                # or implement a password reset flow for Supabase users
                
                # Try local DB first for existing user
                c.execute("SELECT id, email, full_name, password_hash, organization, role, status FROM users WHERE email = ?", 
                             (request.email,))
                local_user = c.fetchone()
                
                if local_user:
                    # User exists in both places - verify password against local hash
                    user_id, email, full_name, password_hash, organization, role, local_status = local_user
                    print(f"✅ Found user in local DB - verifying password")
                    
                    if not verify_password(request.password, password_hash):
                        print(f"❌ Password verification failed for local user")
                        raise HTTPException(status_code=401, detail="⚠️ كلمة المرور غير صحيحة")
                    
                    print(f"✅ Local password verification successful")
                    
                    # Sync data with Supabase if needed
                    if (local_status != sb_status or organization != sb_organization or full_name != sb_full_name):
                        print(f"🔄 Syncing local data with Supabase")
                        c.execute("""
                            UPDATE users 
                                SET status = ?, role = ?, organization = ?, full_name = ? 
                                WHERE email = ?
                            """, (sb_status, sb_role, sb_organization, sb_full_name, email))
                        conn.commit()
                    
                    print(f"🎉 SUCCESS: Login approved for {request.email}")
                    
                    token = generate_token(user_id, email, organization, role)
                    
                    # Update last login in Supabase
                    try:
                        supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("email", email).execute()
                    except Exception as sync_error:
                        print(f"⚠️ Supabase sync error: {sync_error}")
                        # Continue without failing the login
                    
                    return {
                        "token": token,
                        "user": {
                            "id": user_id,
                            "email": email,
                            "full_name": full_name,
                            "organization": organization,
                            "role": role,
                            "status": local_status
                        }
                    }
                else:
                    # User exists in Supabase but not in local DB - create local record
                    print(f"🔄 Creating local user from Supabase data")
                    password_hash = hash_password(request.password)  # Store the provided password
                    
                    c.execute("""
                        INSERT INTO users (email, full_name, password_hash, organization, role, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (sb_email, sb_full_name, password_hash, sb_organization, sb_role, sb_status, datetime.now()))
                    conn.commit()
                    
                    user_id = c.lastrowid
                    print(f"✅ Created local user from Supabase data")
                    
                    print(f"🎉 SUCCESS: Login approved for {request.email}")
                    
                    token = generate_token(user_id, sb_email, sb_organization, sb_role)
                    
                    # Update last login in Supabase
                    try:
                        supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("email", sb_email).execute()
                    except Exception as sync_error:
                        print(f"⚠️ Supabase sync error: {sync_error}")
                        # Continue without failing the login
                    
                    return {
                        "token": token,
                        "user": {
                            "id": user_id,
                            "email": sb_email,
                            "full_name": sb_full_name,
                            "organization": sb_organization,
                            "role": sb_role,
                            "status": sb_status
                        }
                    }
            else:
                print(f"❌ User {request.email} not approved in Supabase (status: {sb_status})")
                raise HTTPException(status_code=403, detail="⚠️ حسابك قيد المراجعة. يرجى انتظار موافقة المسؤول")
        
        # If Supabase fails, try local database as fallback
        print(f"🔍 Step 2: Checking local database as fallback...")
        c.execute("SELECT id, email, full_name, password_hash, organization, role, status FROM users WHERE email = ?", 
                 (request.email,))
        user_data = c.fetchone()
        
        if user_data:
            user_id, email, full_name, password_hash, organization, role, local_status = user_data
            print(f"✅ User {request.email} found in local database")
            print(f"   Status: {local_status}")
            
            # Check if user is approved
            if local_status != 'approved':
                print(f"❌ User {request.email} is not approved (status: {local_status})")
                raise HTTPException(status_code=403, detail="⚠️ حسابك قيد المراجعة. يرجى انتظار موافقة المسؤول")
            
            # Verify password
            print(f"🔍 Step 3: Verifying password...")
            if not verify_password(request.password, password_hash):
                print(f"❌ Password verification failed for {request.email}")
                raise HTTPException(status_code=401, detail="⚠️ كلمة المرور غير صحيحة")
            
            print(f"✅ Password verification successful")
            print(f"🎉 SUCCESS: Login approved for {request.email}")
            
            token = generate_token(user_id, email, organization, role)
            
            # Update last login in Supabase (try to sync)
            try:
                supabase.table("users").update({"last_login": datetime.now().isoformat()}).eq("email", email).execute()
            except Exception as sync_error:
                print(f"⚠️ Supabase sync error: {sync_error}")
                # Continue without failing the login
            
            return {
                "token": token,
                "user": {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "organization": organization,
                    "role": role,
                    "status": local_status
                }
            }
        
        print(f"❌ User {request.email} not found in Supabase or local database")
        raise HTTPException(status_code=401, detail="⚠️ المستخدم غير موجود. يرجى التسجيل أولاً")
        
    except HTTPException as e:
        print(f"❌ HTTP Exception: {e}")
        raise e
    except Exception as e:
        print(f"❌ General Exception: {e}")
        raise HTTPException(status_code=500, detail="فشل في المصادقة. يرجى المحاولة مرة أخرى")
    finally:
        conn.close()

@router.post("/signup-requests/{request_id}/approve")
async def approve_signup(request_id: str, email: Optional[str] = None):
    """Approve a signup request and sync with Supabase"""
    
    # Always check local database first to ensure user is moved to 'users' table
    init_db()
    conn = get_db()
    c = conn.cursor()
    
    try:
        # First, try to sync status in Supabase
        supabase_synced = False
        supabase_error = None
        user_email = email
        user_id_in_sb = None
        
        try:
            print(f"DEBUG: Starting approval for ID: {request_id}, Email: {user_email}")
            
            # 1. Try finding by Email if provided (most robust for Supabase)
            sb_response = None
            if user_email:
                sb_response = supabase.table("users").select("*").eq("email", user_email).execute()
                if sb_response.data and len(sb_response.data) > 0:
                    print(f"DEBUG: Found user in Supabase by provided email: {user_email}")

            # 2. Try finding by ID (as string) if not found by email
            if not (sb_response and sb_response.data and len(sb_response.data) > 0):
                sb_response = supabase.table("users").select("*").eq("id", request_id).execute()
                if sb_response.data and len(sb_response.data) > 0:
                    print(f"DEBUG: Found user in Supabase by ID (string): {request_id}")
            
            # 3. Try finding by ID (as integer) if not found
            if not (sb_response and sb_response.data and len(sb_response.data) > 0):
                try:
                    int_id = int(request_id)
                    sb_response = supabase.table("users").select("*").eq("id", int_id).execute()
                    if sb_response.data and len(sb_response.data) > 0:
                        print(f"DEBUG: Found user in Supabase by ID (int): {int_id}")
                except (ValueError, TypeError):
                    pass
            
            # 4. Try finding by Email locally first to then find in Supabase by Email (Fallback)
            if not (sb_response and sb_response.data and len(sb_response.data) > 0):
                # Check local DB for email associated with this ID
                c.execute("SELECT email FROM signup_requests WHERE id = ?", (request_id,))
                local_res = c.fetchone()
                if local_res:
                    temp_email = local_res[0]
                    sb_response = supabase.table("users").select("*").eq("email", temp_email).execute()
                    print(f"DEBUG: Found user in Supabase by local email lookup: {temp_email}")

            # 5. Process Supabase result if found
            if sb_response and sb_response.data and len(sb_response.data) > 0:
                user_data = sb_response.data[0]
                user_email = user_data.get("email")
                user_id_in_sb = user_data.get("id")
                
                # Update status in Supabase
                try:
                    # Try update by ID (most precise)
                    supabase.table("users").update({"status": "approved"}).eq("id", user_id_in_sb).execute()
                    supabase_synced = True
                    print(f"✅ Approved {user_email} in Supabase by ID: {user_id_in_sb}")
                except Exception as e1:
                    print(f"⚠️ Supabase update by ID failed: {e1}")
                    try:
                        # Fallback to update by email
                        supabase.table("users").update({"status": "approved"}).eq("email", user_email).execute()
                        supabase_synced = True
                        print(f"✅ Approved {user_email} in Supabase by Email")
                    except Exception as e2:
                        print(f"❌ Supabase update by Email failed: {e2}")
                        supabase_error = str(e2)
            else:
                print(f"DEBUG: User {request_id} / {user_email} NOT found in Supabase by any method")
        except Exception as se:
            print(f"⚠️ Supabase general operation failed: {se}")
            supabase_error = str(se)

        # Now handle local database approval
        # Try to find the request locally by ID OR Email
        request_data = None
        c.execute("SELECT * FROM signup_requests WHERE id = ?", (request_id,))
        request_data = c.fetchone()
        
        if not request_data and user_email:
            c.execute("SELECT * FROM signup_requests WHERE email = ?", (user_email,))
            request_data = c.fetchone()
        
        if not request_data:
            # If not in signup_requests, check if already in users
            c.execute("SELECT id, status FROM users WHERE id = ?", (request_id,))
            if c.fetchone():
                return {"message": "تمت الموافقة على الحساب بالفعل"}
            
            if user_email:
                c.execute("SELECT id, status FROM users WHERE email = ?", (user_email,))
                if c.fetchone():
                    return {"message": "تمت الموافقة على الحساب بالفعل (تم العثور عليه بالبريد الإلكتروني)"}
            
            # If we synced to Supabase but not found locally, it might be a Supabase-only user
            if supabase_synced:
                return {"message": "تمت الموافقة على الحساب في Supabase بنجاح"}
                
            error_msg = "الطلب غير موجود"
            if supabase_error:
                error_msg += f" (Supabase: {supabase_error})"
            raise HTTPException(status_code=404, detail=error_msg)
        
        rid, email, full_name, password_hash, organization, role, status, reason, created_at, reviewed_at, reviewed_by = request_data
        
        # Check if user already exists in users table by email
        c.execute("SELECT id, status FROM users WHERE email = ?", (email,))
        existing_user = c.fetchone()
        
        if existing_user:
            uid, current_status = existing_user
            c.execute("UPDATE users SET status = 'approved' WHERE id = ?", (uid,))
            c.execute("DELETE FROM signup_requests WHERE id = ?", (rid,))
            conn.commit()
            print(f"✅ User {email} updated to approved in local DB")
            return {"message": "تم تحديث حالة الحساب بنجاح"}
        
        # Move from signup_requests to users table
        c.execute('''
            INSERT INTO users (id, email, full_name, password_hash, organization, role, status)
            VALUES (?, ?, ?, ?, ?, ?, 'approved')
        ''', (rid, email, full_name, password_hash, organization, role))
        
        c.execute("DELETE FROM signup_requests WHERE id = ?", (rid,))
        conn.commit()
        
        print(f"✅ Approved user {email} in local DB and moved to users table")
        return {"message": "تمت الموافقة على الحساب بنجاح"}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, authorization: str = Header(None)):
    """Delete a user from both local DB and Supabase (Admin Only) - Strongest Version"""
    print(f"DEBUG: DELETE /auth/users/{user_id} requested")
    
    if not authorization:
        raise HTTPException(status_code=401, detail="التوكن مفقود")
    
    token = authorization.replace("Bearer ", "")
    token_data = decode_token(token)
    if not token_data or token_data.get("role") != 'admin':
        raise HTTPException(status_code=403, detail="غير مصرح لك بحذف المستخدمين")
    
    # 1. Try to find the user in Supabase FIRST since the frontend uses Supabase data
    email_to_delete = None
    try:
        # Try finding by ID (as string and as integer)
        sb_res = supabase.table("users").select("email").eq("id", user_id).execute()
        if not sb_res.data:
            try:
                # Try integer cast for Supabase
                int_id = int(user_id)
                sb_res = supabase.table("users").select("email").eq("id", int_id).execute()
            except ValueError:
                pass
        
        if sb_res.data and len(sb_res.data) > 0:
            email_to_delete = sb_res.data[0].get("email")
            print(f"DEBUG: Found user in Supabase with email: {email_to_delete}")
    except Exception as e:
        print(f"⚠️ Supabase lookup failed: {e}")

    # 2. Perform Deletion in Supabase
    try:
        print(f"DEBUG: Attempting Supabase deletion for ID: {user_id}")
        # Delete by ID (string)
        res1 = supabase.table("users").delete().eq("id", user_id).execute()
        
        # Delete by ID (int)
        res2 = None
        try:
            int_id = int(user_id)
            res2 = supabase.table("users").delete().eq("id", int_id).execute()
        except: pass
        
        # Delete by Email if found
        res3 = None
        if email_to_delete:
            res3 = supabase.table("users").delete().eq("email", email_to_delete).execute()
            
        print(f"✅ Supabase deletion attempts finished. Results: ID(str): {len(res1.data) if res1.data else 0}, ID(int): {len(res2.data) if res2 and res2.data else 0}, Email: {len(res3.data) if res3 and res3.data else 0}")
    except Exception as e:
        print(f"⚠️ Supabase deletion error: {e}")

    # 3. Perform Deletion in Local DB
    init_db()
    conn = get_db()
    c = conn.cursor()
    try:
        # Delete by ID (as is)
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        c.execute("DELETE FROM signup_requests WHERE id = ?", (user_id,))
        
        # Delete by integer ID if possible
        try:
            int_id = int(user_id)
            c.execute("DELETE FROM users WHERE id = ?", (int_id,))
            c.execute("DELETE FROM signup_requests WHERE id = ?", (int_id,))
        except: pass
        
        # Delete by Email if found
        if email_to_delete:
            c.execute("DELETE FROM users WHERE email = ?", (email_to_delete,))
            c.execute("DELETE FROM signup_requests WHERE email = ?", (email_to_delete,))
            
        conn.commit()
        print(f"✅ Deleted user from local DB")
        
        # We return success even if not found locally, as long as we tried Supabase
        return {"message": "تم حذف المستخدم بنجاح"}
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Local DB deletion error: {e}")
        raise HTTPException(status_code=500, detail="فشل حذف المستخدم من قاعدة البيانات المحلية")
    finally:
        conn.close()

@router.get("/users")
async def get_users(authorization: str = Header(None)):
    """Get users, preferring Supabase if available"""
    print(f"DEBUG: GET /auth/users called with Auth: {authorization[:20] if authorization else 'None'}")
    if not authorization:
        raise HTTPException(status_code=401, detail="التوكن مفقود")
    
    token = authorization.replace("Bearer ", "")
    token_data = decode_token(token)
    if not token_data or token_data.get("role") != 'admin':
        print(f"DEBUG: Auth failed. TokenData: {token_data}")
        raise HTTPException(status_code=403, detail="غير مصرح لك بالوصول")
        
    # Get all users (System Admin view)
    print(f"DEBUG: Fetching ALL users")
    users = []

    # Try Supabase first
    try:
        response = supabase.table("users").select("*").execute()
        if response.data and len(response.data) > 0:
            # Ensure status exists for all users
            users_from_supabase = []
            for u in response.data:
                if 'status' not in u or not u['status']:
                    u['status'] = 'approved'
                users_from_supabase.append(u)
            users.extend(users_from_supabase)
            print(f"DEBUG: Got {len(users_from_supabase)} users from Supabase")
    except Exception as e:
        print(f"Supabase error: {e}")
        pass

    # Also get users from local database and merge
    init_db()
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('SELECT id, email, full_name, organization, role, status, created_at FROM users')
        users_list = c.fetchall()
        local_users = [{"id": r[0], "email": r[1], "full_name": r[2], "organization": r[3], "role": r[4], "status": r[5], "created_at": r[6]} for r in users_list]
        print(f"DEBUG: Got {len(local_users)} users from local DB")
        
        # Merge lists, avoiding duplicates by email (prioritizing Supabase data)
        existing_emails = {u['email'] for u in users}
        for u in local_users:
            if u['email'] not in existing_emails:
                users.append(u)
        
        print(f"DEBUG: Total merged users: {len(users)}")
        return {"users": users}
    finally:
        conn.close()

@router.get("/signup-requests")
async def get_signup_requests(authorization: str = Header(None)):
    """Get pending signup requests, preferring Supabase if available"""
    if not authorization:
        raise HTTPException(status_code=401, detail="التوكن مفقود")
    
    token = authorization.replace("Bearer ", "")
    token_data = decode_token(token)
    if not token_data or token_data.get("role") != 'admin':
        raise HTTPException(status_code=403, detail="غير مصرح لك بالوصول")
    
    # Get all pending requests
    print(f"DEBUG: Fetching ALL signup requests")

    # Try Supabase first
    try:
        response = supabase.table("users").select("*").eq("status", "pending").execute()
        if response.data and len(response.data) > 0:
            # Ensure status exists for all requests
            requests_from_supabase = []
            for r in response.data:
                if 'status' not in r or not r['status']:
                    r['status'] = 'pending'
                requests_from_supabase.append(r)
            return {"requests": requests_from_supabase}
    except Exception as e:
        print(f"Supabase error: {e}")
        pass

    # Fallback to Local DB
    init_db()
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('SELECT id, email, full_name, organization, role, status, created_at FROM signup_requests WHERE status = "pending"')
        requests_list = c.fetchall()
        requests = [{"id": r[0], "email": r[1], "full_name": r[2], "organization": r[3], "role": r[4], "status": r[5], "created_at": r[6]} for r in requests_list]
        return {"requests": requests}
    finally:
        conn.close()

@router.patch("/users/{user_id}")
async def update_user(user_id: str, update_data: UserUpdate):
    """Update user information in both local DB and Supabase"""
    
    # 1. Update in Supabase
    supabase_updated = False
    user_email = None
    
    try:
        # Prepare data for update (only non-None fields)
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        if not update_dict:
            return {"message": "No data to update"}
            
        print(f"DEBUG: Updating user {user_id} in Supabase with {update_dict}")
        
        # Try update by ID (string)
        sb_response = supabase.table("users").update(update_dict).eq("id", user_id).execute()
        
        # Try update by ID (integer) if not found
        if not (sb_response.data and len(sb_response.data) > 0):
            try:
                int_id = int(user_id)
                sb_response = supabase.table("users").update(update_dict).eq("id", int_id).execute()
            except (ValueError, TypeError):
                pass
                
        if sb_response.data and len(sb_response.data) > 0:
            supabase_updated = True
            user_email = sb_response.data[0].get("email")
            print(f"✅ Updated user {user_id} in Supabase")
        else:
            print(f"⚠️ User {user_id} not found in Supabase for update")
            
    except Exception as e:
        print(f"❌ Supabase update failed: {e}")

    # 2. Update in Local SQLite
    init_db()
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Build update query for local DB
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        if update_dict:
            fields = ", ".join([f"{k} = ?" for k in update_dict.keys()])
            values = list(update_dict.values())
            
            # Update by ID
            c.execute(f"UPDATE users SET {fields} WHERE id = ?", (*values, user_id))
            
            # If we have an email from Supabase, try updating by email too as a fallback
            if user_email:
                c.execute(f"UPDATE users SET {fields} WHERE email = ?", (*values, user_email))
            
            conn.commit()
            print(f"✅ Updated user {user_id} in local SQLite")
            
        return {"message": "User updated successfully"}
        
    except Exception as e:
        print(f"❌ Local DB update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/signup-requests/{request_id}/decline")
async def decline_signup(request_id: str, request: DeclineRequest):
    """Decline a signup request by updating status to declined"""
    
    # Always check local database first
    init_db()
    conn = get_db()
    c = conn.cursor()
    
    try:
        # First try to find and update in Supabase
        supabase_synced = False
        supabase_error = None
        user_email = None
        user_id_in_sb = None
        
        try:
            print(f"DEBUG: Starting decline for {request_id}")
            
            # 1. Try finding by ID (as string)
            sb_response = supabase.table("users").select("*").eq("id", request_id).execute()
            
            # 2. Try finding by ID (as integer) if not found
            if not (sb_response.data and len(sb_response.data) > 0):
                try:
                    int_id = int(request_id)
                    sb_response = supabase.table("users").select("*").eq("id", int_id).execute()
                except (ValueError, TypeError):
                    pass
            
            # 3. Try finding by Email locally first to then find in Supabase by Email
            if not (sb_response.data and len(sb_response.data) > 0):
                # Check local DB for email associated with this ID
                c.execute("SELECT email FROM signup_requests WHERE id = ?", (request_id,))
                local_res = c.fetchone()
                if local_res:
                    temp_email = local_res[0]
                    sb_response = supabase.table("users").select("*").eq("email", temp_email).execute()
                    print(f"DEBUG: Found user in Supabase by local email: {temp_email}")

            # 4. Process Supabase result if found
            if sb_response.data and len(sb_response.data) > 0:
                user_data = sb_response.data[0]
                user_email = user_data.get("email")
                user_id_in_sb = user_data.get("id")
                print(f"DEBUG: Found user {user_email} in Supabase")
                
                # Update status in Supabase
                try:
                    # Try update by ID (most precise)
                    supabase.table("users").update({"status": "declined"}).eq("id", user_id_in_sb).execute()
                    supabase_synced = True
                    print(f"✅ Declined {user_email} in Supabase by ID")
                except Exception as e1:
                    print(f"⚠️ Supabase decline by ID failed: {e1}")
                    try:
                        # Fallback to update by email
                        supabase.table("users").update({"status": "declined"}).eq("email", user_email).execute()
                        supabase_synced = True
                        print(f"✅ Declined {user_email} in Supabase by Email")
                    except Exception as e2:
                        print(f"❌ Supabase decline by Email failed: {e2}")
                        supabase_error = str(e2)
            else:
                print(f"DEBUG: User {request_id} NOT found in Supabase by any method")
        except Exception as se:
            print(f"⚠️ Supabase general operation failed during decline: {se}")
            supabase_error = str(se)

        # Now handle local database decline
        # Try to find the request locally by ID OR Email
        request_data = None
        c.execute("SELECT * FROM signup_requests WHERE id = ?", (request_id,))
        request_data = c.fetchone()
        
        if not request_data and user_email:
            c.execute("SELECT * FROM signup_requests WHERE email = ?", (user_email,))
            request_data = c.fetchone()
        
        if not request_data:
            # If not in signup_requests, check if already in users
            c.execute("SELECT id, status FROM users WHERE id = ?", (request_id,))
            if c.fetchone():
                c.execute("UPDATE users SET status = 'declined' WHERE id = ?", (request_id,))
                conn.commit()
                return {"message": "تم رفض الحساب بالفعل (تحديث الحالة)"}
            
            if user_email:
                c.execute("SELECT id, status FROM users WHERE email = ?", (user_email,))
                if c.fetchone():
                    c.execute("UPDATE users SET status = 'declined' WHERE email = ?", (user_email,))
                    conn.commit()
                    return {"message": "تم رفض الحساب بالفعل (تحديث الحالة بالبريد الإلكتروني)"}
            
            # If we synced to Supabase but not found locally, it might be a Supabase-only user
            if supabase_synced:
                return {"message": "تم رفض الحساب في Supabase بنجاح"}
                
            error_msg = "الطلب غير موجود"
            if supabase_error:
                error_msg += f" (Supabase: {supabase_error})"
            raise HTTPException(status_code=404, detail=error_msg)
        
        rid, email, full_name, password_hash, organization, role, status, reason, created_at, reviewed_at, reviewed_by = request_data
        
        # 1. Move user from signup_requests to users table with declined status
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_user = c.fetchone()
        
        if existing_user:
            uid = existing_user[0]
            c.execute("UPDATE users SET status = 'declined' WHERE id = ?", (uid,))
        else:
            c.execute('''
                INSERT INTO users (id, email, full_name, password_hash, organization, role, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'declined', ?)
            ''', (rid, email, full_name, password_hash, organization, role, created_at))
        
        c.execute("DELETE FROM signup_requests WHERE id = ?", (rid,))
        conn.commit()
        
        print(f"✅ Rejected user {email} moved to users table with declined status")
        return {"message": "تم رفض الحساب بنجاح"}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/organization-users")
async def get_organization_users(organization: str, authorization: str = Header(None)):
    """Get all approved users for a specific organization, prioritizing Supabase"""
    print(f"DEBUG: Fetching users for organization: '{organization}'")
    if not authorization:
        raise HTTPException(status_code=401, detail="التوكن مفقود")
    
    token = authorization.replace("Bearer ", "")
    token_data = decode_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="توكن غير صالح")

    # Clean the organization name to handle any whitespace issues
    organization = organization.strip()

    users = []
    
    # Try Supabase first for most up-to-date data
    try:
        # Search in Supabase - handle both 'approved' and potentially missing status
        response = supabase.table("users").select("*").eq("organization", organization).execute()
        if response.data:
            # Filter in Python to handle the status flexibility
            sb_users = [u for u in response.data if u.get('status') in ['approved', None, '']]
            print(f"DEBUG: Supabase found {len(sb_users)} users for '{organization}'")
            print(f"DEBUG: Supabase user emails: {[u['email'] for u in sb_users]}")
            users.extend(sb_users)
                    
    except Exception as e:
        print(f"Supabase error fetching org users: {e}")
        # Continue to local DB fallback

    # Fallback to local DB if Supabase failed or to supplement data
    init_db()
    conn = get_db()
    c = conn.cursor()
    try:
        # Fetch users for this organization - being more lenient with status (approved or null)
        c.execute('''
            SELECT id, email, full_name, organization, role, status, created_at 
            FROM users 
            WHERE TRIM(organization) = ? 
            AND (status = 'approved' OR status IS NULL OR status = '')
        ''', (organization,))
        users_list = c.fetchall()
        local_users = [{"id": r[0], "email": r[1], "full_name": r[2], "organization": r[3], "role": r[4], "status": r[5] or 'approved', "created_at": r[6]} for r in users_list]
        
        print(f"DEBUG: Local DB found {len(local_users)} users for '{organization}'")
        print(f"DEBUG: Local DB user emails: {[u['email'] for u in local_users]}")
        
        # Merge lists, avoiding duplicates by email (prioritizing Supabase data)
        existing_emails = {u['email'] for u in users}
        for u in local_users:
            if u['email'] not in existing_emails:
                users.append(u)
                existing_emails.add(u['email'])
        
        # Final deduplication - ensure unique emails
        unique_users = {}
        for u in users:
            if u['email'] not in unique_users:
                unique_users[u['email']] = u
        users = list(unique_users.values())
        
        print(f"DEBUG: Final unique users count: {len(users)}")
        print(f"DEBUG: Final user emails: {[u['email'] for u in users]}")
        
    except Exception as e:
        print(f"Local DB error fetching org users: {e}")
    finally:
        conn.close()

    return {"users": users}
