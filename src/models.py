from .database import Base
from datetime import datetime
from sqlalchemy import Column,Integer,String,Boolean,DateTime # type: ignore
from sqlalchemy.ext.declarative import declarative_base # type: ignore
from sqlalchemy.dialects.postgresql import ARRAY # type: ignore

Base = declarative_base()


class Incident(Base):
    """
    This class represents a service incident.

    Attributes:
        __tablename__ (str): The name of the table in the database.
        id (int): The unique identifier of the incident.
        affected_products (List[str]): The list of affected products.
        severity (str): The severity of the incident.
        suspected_owning_team (List[str]): The list of suspected owning teams.
        start_time (datetime): The start time of the incident.
        end_time (datetime): The end time of the incident.
        p1_customer_affected (bool): Whether the incident affects P1 customers.
        suspected_affected_components (List[str]): The list of suspected affected components.
        description (str): The description of the incident.
        message_for_sp (str): The message for the service provider.
        statuspage_notification (bool): Whether a notification should be sent to the statuspage.
        separate_channel_creation (bool): Whether a separate channel should be created.
        status (str): The status of the incident.
        created_at (datetime): The creation time of the incident.
    """
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