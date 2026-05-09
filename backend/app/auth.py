"""Firebase Auth integration for backend.

Verifies Firebase ID tokens and maps users to local RBAC roles.
Uses firebase-admin SDK for token verification.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from .db import connect

import json
import logging
from .config import settings

logger = logging.getLogger(__name__)

# ── Firebase Admin init ──────────────────────────────────────────
_firebase_app = None

def _init_firebase():
    global _firebase_app
    if _firebase_app is not None:
        return

    try:
        if settings.FIREBASE_SERVICE_ACCOUNT_JSON.strip():
            # ✅ Production: load from env var string
            logger.info("Initializing Firebase from environment variable")
            cred_dict = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            cred = credentials.Certificate(cred_dict)
        else:
            # ✅ Local dev: load from JSON file
            logger.info("Initializing Firebase from local service account file")
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)

        _firebase_app = firebase_admin.initialize_app(cred, {
            "projectId": settings.FIREBASE_PROJECT_ID,
        })
        logger.info("Firebase initialized successfully")
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")
        # Fallback for local dev if file is missing
        if not settings.FIREBASE_SERVICE_ACCOUNT_JSON.strip():
             try:
                 _firebase_app = firebase_admin.initialize_app(options={"projectId": settings.FIREBASE_PROJECT_ID})
             except Exception:
                 pass

_init_firebase()


# ── Token verification ───────────────────────────────────────────
security = HTTPBearer(auto_error=False)


def verify_firebase_token(token: str) -> dict[str, Any]:
    """Verify a Firebase ID token and return the decoded claims."""
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Authentication failed: {str(e)}")


# ── User sync / lookup ───────────────────────────────────────────
VALID_ROLES = {"pending", "operator", "supervisor", "quality", "manager", "admin"}


def get_or_create_user(firebase_uid: str, email: str | None, display_name: str | None = None) -> dict[str, Any]:
    """Find existing user by firebase_uid or create a new one.
    
    NOTE: Currently modified to grant 'admin' to everyone for easier deployment evaluation.
    """
    conn = connect()
    try:
        from .config import settings
        
        # Look up by firebase_uid
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (firebase_uid,)).fetchone()
        if row:
            user_dict = dict(row)
            # FORCE UPGRADE: Everyone is an admin for now
            if user_dict.get("role") != "admin":
                conn.execute("UPDATE users SET role = 'admin' WHERE user_id = ?", (firebase_uid,))
                conn.commit()
                user_dict["role"] = "admin"
            return user_dict

        # Look up by email (migration from old system)
        if email:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row:
                # Update to use Firebase UID and enforce admin
                conn.execute("UPDATE users SET user_id = ?, role = 'admin' WHERE email = ?", (firebase_uid, email))
                conn.commit()
                return {**dict(row), "user_id": firebase_uid, "role": "admin"}

        # Auto-create new user with 'admin' role
        conn.execute(
            "INSERT INTO users (user_id, email, password_hash, full_name, role, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            (firebase_uid, email or f"{firebase_uid}@firebase", "FIREBASE_AUTH", display_name or "", "admin", 1),
        )
        conn.commit()
        return {
            "user_id": firebase_uid,
            "email": email or f"{firebase_uid}@firebase",
            "full_name": display_name or "",
            "role": "admin",
            "is_active": 1,
        }
    finally:
        conn.close()


def update_user_role(user_id: str, new_role: str) -> dict[str, Any]:
    """Update a user's role (admin only)."""
    if new_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
    conn = connect()
    try:
        conn.execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, user_id))
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(row)
    finally:
        conn.close()


# ── FastAPI dependencies ─────────────────────────────────────────

async def get_current_user(creds=Depends(security)) -> dict[str, Any]:
    """Extract and verify the Firebase token, return the local user record with role."""
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    decoded = verify_firebase_token(creds.credentials)
    firebase_uid = decoded.get("uid", "")
    email = decoded.get("email")
    name = decoded.get("name")

    user = get_or_create_user(firebase_uid, email, name)
    return user


def _require_role(*allowed_roles: str):
    """Factory: create a dependency that checks the user's role.
    
    NOTE: Currently modified to allow ANY authenticated user to pass, regardless of role.
    """
    async def checker(user: dict = Depends(get_current_user)):
        # RBAC BYPASSED: Return user immediately
        return user
    return checker


require_admin = _require_role("admin")
require_supervisor_or_above = _require_role("supervisor", "quality", "manager", "admin")
require_quality_or_above = _require_role("quality", "manager", "admin")
require_operator_or_above = _require_role("operator", "supervisor", "quality", "manager", "admin")


# ── Legacy helpers (kept for pipeline.py seed_default_admin) ─────
def get_password_hash(password: str) -> str:
    return "FIREBASE_AUTH"

def get_user_by_email(email: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
