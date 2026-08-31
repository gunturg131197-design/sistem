#!/usr/bin/env python3
"""
Create admin and operator users for testing
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import os
import bcrypt
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def create_users():
    # Check if admin exists
    admin = await db.users.find_one({"username": "admin"})
    if admin:
        print("Admin user already exists")
        # Update password
        await db.users.update_one(
            {"username": "admin"},
            {"$set": {"password_hash": hash_password("admin123")}}
        )
        print("Updated admin password to admin123")
    else:
        # Create admin
        admin_doc = {
            "user_id": "user_admin_seed01",
            "email": "admin@excavaops.local",
            "name": "Admin User",
            "picture": "",
            "role": "admin",
            "manual": True,
            "username": "admin",
            "password_hash": hash_password("admin123"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(admin_doc)
        print("Created admin user (username: admin, password: admin123)")
    
    # Check if operator exists
    operator = await db.users.find_one({"username": "budi"})
    if operator:
        print("Operator user already exists")
        # Update password
        await db.users.update_one(
            {"username": "budi"},
            {"$set": {"password_hash": hash_password("budi123")}}
        )
        print("Updated budi password to budi123")
    else:
        # Create operator
        operator_doc = {
            "user_id": "user_op_seed01",
            "email": "budi@excavaops.local",
            "name": "Budi Operator",
            "picture": "",
            "role": "operator",
            "manual": True,
            "username": "budi",
            "password_hash": hash_password("budi123"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(operator_doc)
        print("Created operator user (username: budi, password: budi123)")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(create_users())
