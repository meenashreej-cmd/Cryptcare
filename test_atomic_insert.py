import os
from sqlalchemy import create_engine, insert, select, literal, exists
from sqlalchemy.orm import sessionmaker
from app.models.audit import AccessLog, AccessActionEnum
from app.db.base import Base

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

new_log_id = "test-id-1"
prev_hash = None

condition = ~exists().where(AccessLog.log_id != None)

sel = select(
    literal(new_log_id).label("log_id"),
    literal("user").label("user_id"),
    literal("res").label("resource_type"),
    literal(AccessActionEnum.READ.value).label("action"),
).where(condition)

stmt = insert(AccessLog).from_select(
    ["log_id", "user_id", "resource_type", "action"],
    sel
)

res = db.execute(stmt)
print(f"Insert 1 rowcount: {res.rowcount}")

res2 = db.execute(stmt)
print(f"Insert 2 rowcount: {res2.rowcount}")

print(db.query(AccessLog).all())
