from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.user_models import UserModel

# Configuration - can be overridden with environment variables
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required for security. Please set a secure secret key.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480")
)  # 8 hours default (mobile-friendly)
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Minimum acceptable issued-at value (seconds since epoch). Any token whose
# ``iat`` claim is earlier than this is rejected, regardless of expiry. The
# default value below is the UTC epoch at the time this fix was written, so
# tokens minted before the type-claim requirement landed are invalidated.
# Operators may override via the MIN_TOKEN_IAT_EPOCH env var (e.g. after a
# secret rotation, set it to the rotation timestamp to revoke all older
# sessions).
MIN_TOKEN_IAT = int(os.getenv("MIN_TOKEN_IAT_EPOCH", "1747526400"))  # 2025-05-18T00:00:00Z


class AuthService:
    def __init__(self):
        self.user_repository = UserRepository()

    def authenticate_user(self, username: str, password: str) -> Optional[UserModel]:
        try:
            user = self.user_repository.get_user_by_username(username)
        except Exception:
            # User not found
            return None
        if not user:
            return None
        if not self.user_repository.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        now = datetime.utcnow()
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update(
            {
                "exp": expire,
                "iat": now,
                "password_change_required": data.get("password_change_required", False),
                # Tag this as an access token so verify_token can reject a
                # refresh token presented on a protected route (CVE-style fix).
                "type": "access",
            }
        )
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        to_encode = data.copy()
        now = datetime.utcnow()
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
        """Decode a JWT and enforce the token's ``type`` claim.

        SECURITY: The ``type`` claim is REQUIRED when ``expected_type`` is
        supplied. Tokens minted before this requirement landed (and any
        attacker-forged token that omits the claim) are rejected with 401.
        This invalidates pre-existing sessions — that is the correct
        outcome for the security fix.

        We also enforce a minimum ``iat`` floor via :data:`MIN_TOKEN_IAT`
        so a single global rotation date can invalidate older tokens
        regardless of expiry.

        Args:
            token: The JWT to decode.
            expected_type: If supplied, raises 401 when the token's ``type``
                claim does not match (or is missing entirely).
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Belt-and-suspenders: tokens older than the configured floor are
        # rejected. The default floor is the timestamp at which this fix
        # was written, so legacy tokens (which we know never carried iat)
        # cannot satisfy it. Tokens missing iat entirely are also rejected.
        iat = payload.get("iat")
        if iat is None or int(iat) < MIN_TOKEN_IAT:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issued before security floor",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if expected_type is not None:
            token_type = payload.get("type")
            # STRICT: the type claim must be present and must match. Missing
            # claims are treated as invalid (previously we silently accepted
            # them as access tokens; that was the bypass the auditor flagged).
            if token_type != expected_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type: expected {expected_type}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return payload

    def get_current_user(self, token: str) -> UserModel:
        # Protected routes always require an access token. A refresh token
        # presented as a Bearer must be rejected with 401.
        payload = self.verify_token(token, expected_type="access")
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Handle guest users - they don't exist in database
        if payload.get("is_guest"):
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"Authenticating guest user: {username}")

            # Get viewer role for guest
            try:
                viewer_role = self.user_repository.get_role_by_name("viewer")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Guest authentication failed: viewer role not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Create mock guest user object
            guest_user = UserModel(
                id=username.replace("guest_", ""),
                username=username,
                email=f"{username}@temporary",
                hashed_password="",  # No password for guests
                is_active=True,
                roles=[viewer_role],
                password_change_required=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            return guest_user

        # Regular user authentication
        try:
            user = self.user_repository.get_user_by_username(username)
        except Exception as e:
            # Log the database error and raise a proper authentication error
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Database error during user authentication: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication database error",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    def has_permission(self, user: UserModel, required_permission: str) -> bool:
        if not user.roles:
            return False

        for role in user.roles:
            if "all" in role.permissions or required_permission in role.permissions:
                return True
        return False
