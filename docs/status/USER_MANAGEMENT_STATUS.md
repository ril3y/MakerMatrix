# User Management System - Status & Recommendations

## ✅ Completed

### 1. Password Confirmation
- **Status**: ✅ DONE
- Added confirm password field to CreateUserModal
- Real-time validation with error message when passwords don't match
- Form validation prevents submission if passwords don't match

### 2. Roles Loading
- **Status**: ✅ FIXED
- Added `get_all_roles()` method to UserRepository
- Backend endpoint: `GET /api/users/roles`
- Frontend now properly loads and displays roles

### 3. Password Security
- **Status**: ✅ SECURE
- Using **pbkdf2_sha256** hashing algorithm
- PBKDF2 is NIST-approved and highly secure
- Passwords are **NEVER stored in plain text**
- Only hashed versions stored in database
- Automatically salted and stretched (many iterations)

## 📋 Current Permission System

### Standard Permissions Available:

**Admin Role:**
```
- all (superuser access)
- parts:read, parts:create, parts:update, parts:delete
- locations:read, locations:create, locations:update, locations:delete
- categories:read, categories:create, categories:update, categories:delete
- users:read, users:create, users:update, users:delete
- tasks:read, tasks:create, tasks:update, tasks:delete, tasks:admin
- csv:import
- printer:use, printer:config
- system:admin
```

**User Role (Standard):**
```
- parts:read, parts:create, parts:update
- locations:read
- categories:read
- tasks:read, tasks:create
- csv:import
- printer:use
```

## 🚧 Missing Features

### 1. API Key Creation Permission
**Recommendation**: Add new permission `api_keys:create`

**Implementation**:
```python
# In role creation
permissions=[
    ...
    "api_keys:read",    # View own API keys
    "api_keys:create",  # Create new API keys
    "api_keys:delete",  # Delete own API keys
    "api_keys:admin"    # View/manage all API keys (admin only)
]
```

**Where to add**:
- Update default roles in database initialization
- Add permission checks in API key routes
- Add UI permission toggle in role management

### 2. Self-Service Password Reset Flow

**Current State**:
- ❌ Users cannot reset their own passwords
- ✅ Admins can reset user passwords via edit modal
- ❌ No "forgot password" functionality

**Recommended Implementation**:

#### Option A: Admin-Only Reset (Simple)
```
1. User contacts admin
2. Admin resets password in user management UI
3. Admin gives user temporary password
4. User forced to change on next login (password_change_required flag)
```

#### Option B: Self-Service Reset (Complex)
```
1. Add "Forgot Password" link on login page
2. User enters email
3. System generates reset token (expires in 1 hour)
4. Send reset link via email (requires email server setup)
5. User clicks link, enters new password
6. Token consumed, password updated
```

**Recommendation**: Start with Option A, add Option B later if needed.

### 3. User Preferences/Settings

**Missing Features**:
- Email notifications toggle
- Default label template preference
- Default printer selection
- UI theme preference per user
- Timezone preference
- Language preference

**Database Addition Needed**:
```python
# In UserModel
preferences: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

# Example preferences:
{
    "notifications_enabled": true,
    "default_printer_id": "uuid",
    "default_label_template_id": "uuid",
    "theme": "dark",
    "timezone": "America/New_York",
    "language": "en"
}
```

## 🧪 Testing Status

### Existing Tests:
- ✅ `test_api_key_system.py` - API key functionality
- ✅ `test_user_authentication_authorization.py` - Auth tests
- ✅ `test_user_routes_smoke.py` - Basic route tests

### Missing Tests:
- ❌ User creation modal validation
- ❌ Password confirmation matching
- ❌ Role assignment during user creation
- ❌ User status toggle (activate/deactivate)
- ❌ User deletion
- ❌ Role CRUD operations
- ❌ Permission-based access control

## 📝 Recommended Next Steps

### Priority 1 (Critical):
1. ✅ Fix roles loading - DONE
2. ✅ Add password confirmation - DONE
3. ⏳ Add comprehensive user management tests
4. ⏳ Implement admin password reset flow

### Priority 2 (Important):
5. ⏳ Add API key creation permission
6. ⏳ Add user preferences system
7. ⏳ Add password strength requirements (complexity)

### Priority 3 (Nice to Have):
8. ⏳ Self-service password reset
9. ⏳ Email verification on signup
10. ⏳ 2FA/MFA support

## 🔐 Security Best Practices (Already Implemented)

✅ Password hashing with pbkdf2_sha256
✅ JWT token-based authentication
✅ Role-based access control (RBAC)
✅ API key authentication support
✅ Password change required flag
✅ User active/inactive status
✅ Password length validation (min 8 chars)

## 🛠️ Quick Fixes Needed

### Fix 1: Add API Key Permission Check
```python
# In routers/api_key_routes.py
@router.post("/")
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: UserModel = Depends(get_current_user)
):
    # Add permission check
    if not has_permission(current_user, "api_keys:create"):
        raise HTTPException(403, "Insufficient permissions")
    ...
```

### Fix 2: Add Password Strength Validation
```python
def validate_password_strength(password: str) -> bool:
    """
    Require:
    - Min 8 characters
    - At least one uppercase
    - At least one lowercase
    - At least one number
    - At least one special character
    """
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True
```

## 📊 Current Database Schema

```sql
-- Users Table
CREATE TABLE usermodel (
    id VARCHAR PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,  -- pbkdf2_sha256 hash
    is_active BOOLEAN DEFAULT TRUE,
    password_change_required BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Roles Table
CREATE TABLE rolemodel (
    id VARCHAR PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description VARCHAR,
    permissions JSON  -- Array of permission strings
);

-- User-Role Link (Many-to-Many)
CREATE TABLE userrolelink (
    user_id VARCHAR REFERENCES usermodel(id),
    role_id VARCHAR REFERENCES rolemodel(id),
    PRIMARY KEY (user_id, role_id)
);

-- API Keys Table
CREATE TABLE apikeymodel (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES usermodel(id),
    key_hash VARCHAR UNIQUE NOT NULL,  -- SHA256 hash
    key_prefix VARCHAR,
    name VARCHAR NOT NULL,
    permissions JSON,  -- Array of permission strings
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP,
    last_used_at TIMESTAMP
);
```
