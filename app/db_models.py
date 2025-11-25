from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class HeartRateDataDB(Base):
    __tablename__ = 'heart_rate_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )


class VideoDataDB(Base):
    __tablename__ = 'video_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    session_id = Column(String(255), nullable=False)
    frame_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    format = Column(String(50), nullable=False, default='jpg')

    s3_path = Column(String(512), nullable=False)
    local_path = Column(String(512), nullable=False)

    file_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
        Index("idx_session", "session_id", "frame_id"),
        Index("idx_user_session", "user_id", "session_id")
    )


class UserDataDB(Base):
    __tablename__ = 'user_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
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
    user_id = Column(String(255), nullable=False)
    task = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )


class BioDataDB(Base):
    __tablename__ = 'bio_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    value_1 = Column(Float, nullable=True)
    value_2 = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )