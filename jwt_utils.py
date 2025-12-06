"""
JWT Authentication Utilities
Handles JWT token creation, validation, and user extraction
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from database import get_db
from models import User

# Load environment variables
load_dotenv()

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this-in-production')
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '1440'))  # 24 hours default
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7'))  # 7 days default

# Security
security = HTTPBearer()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Dictionary containing user information to encode
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token with longer expiration
    
    Args:
        data: Dictionary containing user information to encode
    
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """
    Verify and decode a JWT token
    
    Args:
        token: JWT token string to verify
        expected_type: Expected token type ("access" or "refresh")
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    print(f"🔑 Verifying token type: {expected_type}")
    print(f"   Token (first 50 chars): {token[:50] if token else 'No token'}...")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Check token type
        token_type = payload.get("type")
        if token_type != expected_type:
            raise credentials_exception
        
        # Check if token is expired (jose handles this automatically, but we can add custom logic)
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
        
    except JWTError as e:
        print(f"JWT Error: {str(e)}")
        raise credentials_exception


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials containing the JWT token
        db: Database session
    
    Returns:
        Current User object
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Check if credentials were provided
    if not credentials:
        print("❌ No credentials provided in request - Authorization header may be missing or malformed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication credentials provided. Please include 'Authorization: Bearer <token>' header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    if not token:
        print("❌ No token in credentials - Bearer token is empty")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided in Bearer authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"🔐 JWT Token received (first 50 chars): {token[:50] if token else 'No token'}...")
    
    # Verify token and get payload
    payload = verify_token(token, expected_type="access")
    print(f"   Token verified successfully. User ID: {payload.get('sub')}, Role: {payload.get('role')}")
    
    # Extract user information
    user_id = payload.get("sub")  # subject (user_id)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"   ❌ User with ID {user_id} not found in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    print(f"   ✅ User found: {user.username} (role: {user.role.role_name if user.role else 'No role'})")
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (convenience function)
    
    Args:
        current_user: Current user from get_current_user
    
    Returns:
        Current active User object
    
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they have admin role
    
    Args:
        current_user: Current user from get_current_user
    
    Returns:
        Current admin User object
    
    Raises:
        HTTPException: If user is not an admin
    """
    # Debug logging
    print(f"🔍 Admin check for user: {current_user.username} (ID: {current_user.id})")
    print(f"   User role: {current_user.role.role_name if current_user.role else 'No role'}")
    print(f"   User role_id: {current_user.role_id}")
    
    if not current_user.role:
        print(f"   ❌ User has no role assigned")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required. (No role assigned)"
        )
    
    if current_user.role.role_name != 'admin':
        print(f"   ❌ User role '{current_user.role.role_name}' is not 'admin'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions. Admin access required. (Current role: {current_user.role.role_name})"
        )
    
    print(f"   ✅ Admin access granted")
    return current_user


def get_current_admin_or_staff_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to verify current user is admin or staff
    
    Args:
        current_user: Current authenticated user from get_current_user
    
    Returns:
        Current admin or staff User object
    
    Raises:
        HTTPException: If user is not an admin or staff
    """
    # Debug logging
    print(f"🔍 Admin/Staff check for user: {current_user.username} (ID: {current_user.id})")
    print(f"   User role: {current_user.role.role_name if current_user.role else 'No role'}")
    print(f"   User role_id: {current_user.role_id}")
    
    if not current_user.role:
        print(f"   ❌ User has no role assigned")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin/Staff access required. (No role assigned)"
        )
    
    # Allow both admin (role_id=1) and staff (role_id=2)
    if current_user.role_id not in [1, 2]:
        print(f"   ❌ User role '{current_user.role.role_name}' is not admin or staff")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions. Admin/Staff access required. (Current role: {current_user.role.role_name})"
        )
    
    print(f"   ✅ Admin/Staff access granted")
    return current_user


def create_tokens_for_user(user: User) -> Dict[str, str]:
    """
    Create both access and refresh tokens for a user
    
    Args:
        user: User object to create tokens for
    
    Returns:
        Dictionary containing access_token and refresh_token
    """
    # Prepare user data for token
    user_data = {
        "sub": str(user.id),  # subject (user_id as string)
        "username": user.username,
        "email": user.email,
        "role": user.role.role_name if user.role else "customer",
        "first_name": user.first_name,
        "last_name": user.last_name
    }
    
    # Create tokens
    access_token = create_access_token(data=user_data)
    refresh_token = create_refresh_token(data=user_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def refresh_access_token(refresh_token: str, db: Session) -> Dict[str, str]:
    """
    Create a new access token using a refresh token
    
    Args:
        refresh_token: Valid refresh token
        db: Database session
    
    Returns:
        Dictionary containing new access_token
    
    Raises:
        HTTPException: If refresh token is invalid or user not found
    """
    # Verify refresh token
    payload = verify_token(refresh_token, expected_type="refresh")
    
    # Get user from database to ensure they still exist and are active
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in refresh token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Verify refresh token from refresh_tokens table
    from models import RefreshToken
    import hashlib
    from datetime import datetime as dt
    
    # Hash the provided token
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    
    # Find the token in database
    refresh_token_record = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.token_hash == token_hash,
        RefreshToken.is_revoked == False
    ).first()
    
    if not refresh_token_record:
        print(f"❌ Refresh token not found in database for user {user.username}")
        print(f"   Token hash: {token_hash[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token - not found or revoked"
        )
    
    # Check if token has expired
    if refresh_token_record.expires_at < dt.utcnow():
        print(f"❌ Refresh token expired for user {user.username}")
        print(f"   Expired at: {refresh_token_record.expires_at}")
        refresh_token_record.is_revoked = True
        refresh_token_record.revoked_at = dt.utcnow()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
    
    # Update last_used_at
    refresh_token_record.last_used_at = dt.utcnow()
    db.commit()
    
    print(f"✅ Refresh token verified from database for user: {user.username}")
    print(f"   Token hash: {token_hash[:20]}...")
    print(f"   Expires at: {refresh_token_record.expires_at}")
    
    # Create new access token with updated user data
    user_data = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role.role_name if user.role else "customer",
        "first_name": user.first_name,
        "last_name": user.last_name
    }
    
    new_access_token = create_access_token(data=user_data)
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }