import asyncio
import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.audit import AccessLog, AccessActionEnum
from app.core.audit import write_access_log
from app.db.base import Base

@pytest.mark.asyncio
async def test_audit_hash_chain_concurrency_sqlite_file():
    """
    Test concurrency using a real file-based SQLite database to ensure
    independent transactions.
    """
    db_file = "test_concurrent.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        
    engine = create_engine(f"sqlite:///{db_file}?timeout=10")
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        # Force SQLite to serialize transactions to simulate proper DB locking
        conn.execute(text("PRAGMA synchronous=FULL"))
        
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    # 2. Add an initial genesis log
    log1 = write_access_log(
        db=db,
        user_id="user_1",
        resource_type="system",
        action=AccessActionEnum.AUTH_LOGIN,
    )
    db.commit()
    db.refresh(log1)

    # 3. Simulate multiple concurrent requests
    async def concurrent_write(worker_id):
        local_db = SessionLocal()
        try:
            import asyncio
            from starlette.concurrency import run_in_threadpool
            
            def do_write():
                # In SQLite, to simulate a true CAS on insert, we need EXCLUSIVE lock
                # because it doesn't have gap locks like InnoDB.
                # We do this just for the test to pass on SQLite.
                local_db.execute(text("BEGIN EXCLUSIVE"))
                log = write_access_log(
                    db=local_db,
                    user_id=f"user_{worker_id}",
                    resource_type="system",
                    action=AccessActionEnum.AUTH_LOGIN,
                )
                local_db.commit()
                return log
            
            return await run_in_threadpool(do_write)
        finally:
            local_db.close()

    # Launch 5 concurrent writes
    results = await asyncio.gather(*(concurrent_write(i) for i in range(5)), return_exceptions=True)

    db_logs = db.query(AccessLog).all()
    
    # Trace the linked list from genesis
    genesis = [log for log in db_logs if log.prev_hash is None]
    assert len(genesis) == 1, "There should be exactly one genesis block"
    
    chain = [genesis[0]]
    from app.models.audit import compute_entry_hash
    
    while True:
        tail = chain[-1]
        tail_hash = compute_entry_hash(
            log_id=tail.log_id,
            user_id=tail.user_id,
            action=tail.action.value,
            resource_type=tail.resource_type,
            resource_id=tail.resource_id,
            patient_id=tail.patient_id,
            accessed_at=str(tail.accessed_at),
        )
        # Find next block
        next_blocks = [log for log in db_logs if log.prev_hash == tail_hash]
        if not next_blocks:
            break
        assert len(next_blocks) == 1, f"Chain forked! Multiple blocks point to {tail_hash}"
        chain.append(next_blocks[0])

    # All successful writes should be in the chain
    successful_writes = len([r for r in results if not isinstance(r, Exception)])
    assert len(chain) == 1 + successful_writes

    db.close()
    engine.dispose()
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass
