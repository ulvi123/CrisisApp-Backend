from .database import Base
from datetime import datetime
from sqlalchemy import Column,Integer,String,Boolean,DateTime # type: ignore
from sqlalchemy.ext.declarative import declarative_base # type: ignore
from sqlalchemy.dialects.postgresql import ARRAY # type: ignore

Base = declarative_base()


class Incident(Base):
    __tablename__ = "service_incidents"
    id = Column(Integer, primary_key=True, index=True)
    affected_products = Column(ARRAY(String), nullable=False)
    severity = Column(String(50),nullable=False)
    suspected_owning_team = Column(ARRAY(String), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    p1_customer_affected = Column(Boolean, default=False, nullable=False)
    suspected_affected_components = Column(ARRAY(String), nullable=False)
    description = Column(String(250), index=True, nullable=False)
    message_for_sp = Column(String(250), nullable=True)
    statuspage_notification = Column(Boolean, default=False, nullable=False)
    separate_channel_creation = Column(Boolean, default=False, nullable=False)
    status = Column(String(50), index=True, nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.now()) 

    def __repr__(self):
        return f"<Incident(id={self.id}, affected_products={self.affected_products}, severity={self.severity}, start_time={self.start_time}, end_time={self.end_time}, status={self.status})>"