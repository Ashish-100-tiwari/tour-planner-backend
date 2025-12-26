"""
Authentication routes for sign up and sign in
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from database import get_database
from bson import ObjectId
import logging
import os

logger = logging.getLogger(__name__)

# Router for auth endpoints
router = APIRouter(prefix="/auth", tags=["authentication"])

# Password hashing
# Password hashing using direct bcrypt
# pwd_context removed as it's incompatible with bcrypt 5.0.0+

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")  # Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/signin")


# Pydantic models
class SignUpRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime


# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    if isinstance(password, str):
        password = password.encode('utf-8')
    # Use default rounds (usually 12)
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_user_by_email(email: str):
    """Get user by email from database"""
    db = get_database()
    if db is None:
        logger.error("Database connection is None in get_user_by_email")
        return None
    try:
        email_lower = email.lower()
        logger.debug(f"Querying database for user with email: {email_lower}")
        user = await db.users.find_one({"email": email_lower})
        if user:
            user["id"] = str(user["_id"])
            del user["_id"]
            logger.debug(f"User found in database: {user.get('email')}")
        else:
            logger.debug(f"No user found in database for email: {email_lower}")
        return user
    except Exception as e:
        logger.error(f"Error querying database for user: {e}")
        return None


async def create_user(user_data: dict):
    """Create a new user in database"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
    
    # Check if user already exists
    existing_user = await get_user_by_email(user_data["email"])
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    user_data["password"] = get_password_hash(user_data["password"])
    user_data["email"] = user_data["email"].lower()
    user_data["created_at"] = datetime.utcnow()
    
    # Remove confirm_password before saving
    user_data.pop("confirm_password", None)
    
    result = await db.users.insert_one(user_data)
    user_data["id"] = str(result.inserted_id)
    user_data.pop("_id", None)
    user_data.pop("password", None)  # Don't return password
    
    return user_data


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_email(email)
    if user is None:
        raise credentials_exception
    
    user.pop("password", None)  # Don't return password
    return user


# Routes
@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignUpRequest):
    """
    User sign up endpoint
    
    - **name**: User's full name (min 2 characters)
    - **email**: User's email address
    - **password**: User's password (min 6 characters)
    - **confirm_password**: Password confirmation (must match password)
    """
    try:
        logger.info(f"Signup attempt for email: {request.email}")
        user_data = request.model_dump()
        user = await create_user(user_data)
        
        logger.info(f"New user registered successfully: {user['email']}")
        
        return UserResponse(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            created_at=user["created_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during registration: {e}"
        )


@router.post("/signin", response_model=TokenResponse)
async def signin(request: SignInRequest):
    """
    User sign in endpoint
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns JWT access token
    """
    try:
        logger.info(f"Signin attempt for email: {request.email}")
        
        # Get user from database
        user = await get_user_by_email(request.email)
        if not user:
            logger.warning(f"Signin failed: User not found for email: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        logger.info(f"User found: {user.get('email')}, verifying password...")
        
        # Verify password
        password_valid = verify_password(request.password, user["password"])
        if not password_valid:
            logger.warning(f"Signin failed: Invalid password for email: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        logger.info(f"Password verified successfully for: {request.email}")
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["email"]},
            expires_delta=access_token_expires
        )
        
        logger.info(f"User signed in: {user['email']}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during signin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during sign in"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information
    Requires valid JWT token in Authorization header
    """
    return UserResponse(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
        created_at=current_user.get("created_at", datetime.utcnow())
    )
