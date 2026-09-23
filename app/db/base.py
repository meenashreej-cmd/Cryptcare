
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models here so Alembic / Base.metadata.create_all() can see them
from app.models.user import *
from app.models.vault import *
from app.models.lab import *
from app.models.nursing import *
from app.models.consent import *
from app.models.insurance import *
from app.models.emergency import *
from app.models.fraud import *
from app.models.notification import *
from app.models.blood_bank import *
from app.models.auth import *

