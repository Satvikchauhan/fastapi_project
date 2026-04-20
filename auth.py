# Used for handling time/date and token expiry
from datetime import UTC, datetime, timedelta

# JWT library used to create and verify tokens
import jwt

# FastAPI OAuth2 helper
# Reads Bearer token from Authorization header
from fastapi.security import OAuth2PasswordBearer

# Password hashing library
# Used to securely hash passwords
from pwdlib import PasswordHash

# Import application settings from config.py
# Example:
# secret_key
# algorithm
# token expiry minutes
from config import settings


# ==================================================
# 🔐 PASSWORD HASHING SETUP
# ==================================================

# Create recommended secure password hashing configuration
# Used for:
# hash_password()
# verify_password()
password_hash = PasswordHash.recommended()


# ==================================================
# 🔑 OAUTH2 TOKEN SCHEME
# ==================================================

# Tells FastAPI where login token endpoint is
# Used in protected routes
# Example Authorization header:
# Bearer eyJhbGciOi...
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/users/token"
)


# ==================================================
# 🔒 HASH PASSWORD
# ==================================================

def hash_password(password: str) -> str:
    """
    Convert plain password into secure hashed password.

    Example:
    "mypassword123"
    ->
    "$argon2id$v=19$..."
    """

    return password_hash.hash(password)


# ==================================================
# 🔍 VERIFY PASSWORD
# ==================================================

def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """
    Compare plain password with stored hashed password.

    Returns:
    True  -> password correct
    False -> password incorrect
    """

    return password_hash.verify(
        plain_password,
        hashed_password
    )


# ==================================================
# 🎟 CREATE ACCESS TOKEN (JWT)
# ==================================================

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None
) -> str:
    """
    Create JWT token.

    Example input:
    {"sub": "1"}

    Output:
    eyJhbGciOiJIUzI1NiIs...
    """

    # Copy original data so we don't modify input
    to_encode = data.copy()

    # If custom expiry passed
    if expires_delta:

        # Set expiration time
        expire = datetime.now(UTC) + expires_delta

    else:
        # Use default expiry from settings
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes,
        )

    # Add expiry claim to token payload
    to_encode.update({"exp": expire})

    # Encode token using secret key + algorithm
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )

    return encoded_jwt


# ==================================================
# ✅ VERIFY ACCESS TOKEN
# ==================================================

def verify_access_token(token: str) -> str | None:
    """
    Verify JWT token.

    If valid:
        returns user id (sub claim)

    If invalid / expired:
        returns None
    """

    try:
        # Decode token
        payload = jwt.decode(
            token,

            # Secret key used to verify signature
            settings.secret_key.get_secret_value(),

            # Allowed algorithm
            algorithms=[settings.algorithm],

            # Require these claims inside token
            options={"require": ["exp", "sub"]},
        )

    # If token invalid / expired / tampered
    except jwt.InvalidTokenError:
        return None

    else:
        # Return subject claim
        # Usually logged-in user ID
        return payload.get("sub")