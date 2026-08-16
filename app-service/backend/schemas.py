from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    filters = relationship("UserFilter", back_populates="user", cascade="all, delete-orphan")

class UserFilter(Base):
    __tablename__ = "user_filters"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    filter_data = Column(JSON, nullable=False)  # словарь с параметрами
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="filters")