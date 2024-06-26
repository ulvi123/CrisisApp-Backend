from .database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship
from datetime import datetime


class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    affected_products = Column(String, index=True)
    severity = Column(String, index=True)
    suspected_owning_team = Column(String, index=True)
    start_time = Column(
        String, index=True
    )#changed from string to datetime, test and ensure it works
    p1_customer_affected = Column(Boolean, default=False)
    suspected_affected_components = Column(String, index=True)
    description = Column(String, index=True)
    message_for_sp = Column(String, nullable=True)
    statuspage_notification = Column(Boolean, default=False)
    separate_channel_creation = Column(Boolean, default=False)
    status = Column(String, index=True)
