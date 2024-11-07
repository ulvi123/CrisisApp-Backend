from .database import Base
from datetime import datetime
from sqlalchemy import Column,Integer,String,Boolean,DateTime
from sqlalchemy.ext.declarative import declarative_base 
from sqlalchemy.dialects.postgresql import ARRAY 
from sqlalchemy import Column, Enum as SQLAlchemyEnum
from enum import Enum

Base = declarative_base()



class UserRole(str,Enum):
    USER = "USER"
    SUPPORT = "SUPPORT"


class Incident(Base):
    __tablename__ = "service_incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    so_number = Column(String(250), index=True, nullable=True,unique=True)
    affected_products = Column(ARRAY(String), nullable=False)
    severity = Column(ARRAY(String), nullable=False)
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
    jira_issue_key = Column(String(250), nullable=True,unique=True)
    statuspage_incident_id = Column(String(250), nullable=True)

    def __repr__(self):
        return f"<Incident(id={self.id}, affected_products={self.affected_products}, severity={self.severity}, start_time={self.start_time}, end_time={self.end_time}, status={self.status}), created_at={self.created_at}), jira_issue_key={self.jira_issue_key}>"
    
    
class UserToken(Base):
    __tablename__ = "user_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(250),unique=True, index=True, nullable=False)
    encrypted_token = Column(String(250), index=True, nullable=False)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.USER,nullable=True,index=True) 
    created_at = Column(DateTime, nullable=True, default=datetime.now())    
  
  
  