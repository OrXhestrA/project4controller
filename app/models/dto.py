from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    field_validator
)
from typing import (
    Dict,
    List,
    Optional
)


class BaseDto(BaseModel):
    """
    DTO基础类
    """
    timestamp: str = Field(..., examples=["2021-01-01 00:00:00"], description="时间戳 YYYY-MM-DD hh:mm:ss")

    @field_validator("timestamp")
    def validate_timestamp(cls, value):
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("Invalid timestamp format")
        return value


class HeartRateDto(BaseDto):
    """
    心率数据
    """
    value: float = Field(
        ...,
        ge=0, le=200,
        description="心率值"
    )

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value
        }


class VideoFrameMetaDto(BaseDto):
    """
    视频帧元数据
    """
    frame_id: int = Field(
        ...,
        ge=0,  # 从0开始
        description="帧ID"
    )


class VideoFrameInfoDto(BaseDto):
    """
    视频帧信息 (返回)
    """
    frame_id: int = Field(..., ge=0, description="帧ID")
    session_id: str = Field(..., description="会话ID")
    format: str = Field(
        default="jpg",
        examples=["jpg", "png", "jpeg"],
        description="帧格式"
    )
    s3_path: str = Field(..., description="S3存储路径")
    local_path: str = Field(..., description="本地存储路径")

    def to_dict(self):
        return {
            "frame_id": self.frame_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "format": self.format,
            "s3_path": self.s3_path,
            "local_path": self.local_path
        }


class TaskDataDto(BaseDto):
    """
    管制任务数据
    """
    task: str = Field(
        ...,
        examples=["task1"],
        description="任务名称"
    )

    def to_dict(self):
        return {
            "task": self.task,
            "timestamp": self.timestamp
        }


class UserDataDto(BaseDto):
    """
    用户数据
    """
    age: int = Field(..., description="年龄")
    gender: int = Field(..., description="性别")
    occupation: str = Field(
        ...,
        examples=["xxx"],
        description="职位"
    )
    tasks: List[TaskDataDto] = Field(
        ...,
        description="任务列表"
    )
    other_info: str = Field(
        ...,
        description="其他信息"
    )

    def to_dict(self) -> Dict:
        return {
            "age": self.age,
            "gender": self.gender,
            "occupation": self.occupation,
            "tasks": [task.to_dict() for task in self.tasks],
            "other_info": self.other_info
        }


class BioValueDto(BaseDto):
    """
    生化数据
    """
    value_1: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="生化数据1"
    )
    value_2: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="生化数据2"
    )


class PredictResultDto(BaseDto):
    """
    预测结果
    """
    predict_mixed: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="混合数据预测结果"
    )
    predict_heart: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="心率数据预测结果"
    )
    predict_video: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="视频数据预测结果"
    )
    predict_stats: str = Field(
        ...,
        description="预测结果状态",
        examples=["1", "2", "3", "4", "5", "6"]
    )

    def to_dict(self, user_id: str):
        return {
            "user_id": user_id,
            "predict_mixed": self.predict_mixed,
            "predict_heart": self.predict_heart,
            "predict_video": self.predict_video,
            "predict_stats": self.predict_stats,
            "timestamp": self.timestamp
        }
