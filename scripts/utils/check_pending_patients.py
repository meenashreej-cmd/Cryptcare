
from app.db.session import engine
from sqlalchemy import text
with engine.connect() as conn:
    res = conn.execute(text("SELECT count(*) FROM users WHERE role='PATIENT' AND status='PENDING_VERIFICATION'"))
    print("COUNT:", res.scalar())

