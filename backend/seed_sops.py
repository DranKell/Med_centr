"""Create missing one-dentist clinic SOP drafts without overwriting local edits."""

from database import Base, SessionLocal, engine
from models.sop import SOP
from sop_catalog import CATALOGUE, build_sop


def seed_sops(db=None) -> int:
    owns_session = db is None
    if owns_session:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
    created = 0
    try:
        existing_keys = {key for (key,) in db.query(SOP.key).all()}
        for category, key, title in CATALOGUE:
            if key in existing_keys:
                continue
            db.add(SOP(**build_sop(category, title, key)))
            existing_keys.add(key)
            created += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_session:
            db.close()
    return created


if __name__ == '__main__':
    print(f'Создано черновиков СОП: {seed_sops()} из {len(CATALOGUE)} тем.')