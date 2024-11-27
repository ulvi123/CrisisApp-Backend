from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import Incident
from src.database import get_db


def generate_next_so_number(db:Session) -> str:
    latest_incident = db.query(Incident).order_by(Incident.id.desc()).first()
    if latest_incident and latest_incident.so_number:
        latest_number = int(latest_incident.so_number.split('-')[1])
        next_number = latest_number + 1
    else:
        next_number = 1
        
    return f"SO-{next_number:04d}"
