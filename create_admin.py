import sys
sys.path.insert(0, '.')
from database import SessionLocal
import models
from auth_utils import hash_password

db = SessionLocal()
admin = models.Admin(
    username      = "admin",
    email         = "admin@debtcall.com",
    password_hash = hash_password("admin123"),
)
db.add(admin)
db.commit()
print("✅ Admin created! Username: admin | Password: admin123")
db.close()