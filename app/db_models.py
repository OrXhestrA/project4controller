from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class HeartRateDataDB(Base):
    __tablename__ = 'heart_rate_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )


class VideoDataDB(Base):
    __tablename__ = 'video_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    format = Column(String(255), nullable=False)
    data = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )


class UserDataDB(Base):
    __tablename__ = 'user_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    gender = Column(Integer, nullable=False)
    occupation = Column(String(255), nullable=False)
    other_info = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )


class TaskDataDB(Base):
    __tablename__ = 'task_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    task = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )


class BioDataDB(Base):
    __tablename__ = 'bio_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    value_1 = Column(Float, nullable=True)
    value_2 = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )