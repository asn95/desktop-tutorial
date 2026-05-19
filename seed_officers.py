from backend.database import SessionLocal, engine, Base
from backend.models import DbUser, UserRole
import uuid

def seed_officers():
    db = SessionLocal()
    
    officers = [
        {"name": "Officer Budi Santoso", "telegram_id": "101"},
        {"name": "Officer Siti Aminah", "telegram_id": "102"},
        {"name": "Officer Agus Hermawan", "telegram_id": "103"},
        {"name": "Officer Mega Pratama", "telegram_id": "104"},
    ]
    
    print("Seeding officers...")
    for off in officers:
        # Check if exists
        existing = db.query(DbUser).filter(DbUser.telegram_id == off["telegram_id"]).first()
        if not existing:
            new_user = DbUser(
                id=str(uuid.uuid4()),
                name=off["name"],
                telegram_id=off["telegram_id"],
                role=UserRole.officer
            )
            db.add(new_user)
            print(f"Added: {off['name']} (ID: {off['telegram_id']})")
        else:
            print(f"Skipped: {off['name']} (Already exists)")
            
    db.commit()
    db.close()
    print("Done!")

if __name__ == "__main__":
    seed_officers()
