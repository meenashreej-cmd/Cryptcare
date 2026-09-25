import os
from sqlalchemy import create_engine, insert, select, literal, exists
from sqlalchemy.orm import sessionmaker
from app.models.audit import AccessLog, AccessActionEnum
from app.db.base import Base

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

# Insert genesis manually
db.execute(insert(AccessLog).values(log_id="gen-id", resource_type="res", action=AccessActionEnum.READ))
db.commit()

new_log_id = "test-id-1"
prev_hash = "fake-hash"

# Condition: no row exists that already uses this prev_hash
condition = ~exists().where(AccessLog.prev_hash == prev_hash)

sel = select(
    literal(new_log_id).label("log_id"),
    literal("user").label("user_id"),
    literal("res").label("resource_type"),
    literal(AccessActionEnum.READ.value).label("action"),
    literal(prev_hash).label("prev_hash")
).where(condition)

stmt = insert(AccessLog).from_select(
    ["log_id", "user_id", "resource_type", "action", "prev_hash"],
    sel
)

res = db.execute(stmt)
print(f"Insert 1 rowcount: {res.rowcount}")

res2 = db.execute(stmt)
print(f"Insert 2 rowcount: {res2.rowcount}")
