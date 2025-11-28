from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    field_validator
)
from typing import (
    List
)
from fastapi import UploadFile
from app.models.dto import (
    HeartRateDto,
    UserDataDto,
    BioValueDto
)


class BaseRequest(BaseModel):
    """
    请求基础类
    """
    user_id: str = Field(..., examples=["0001"], description="用户ID")


class SetParamsRequest(BaseRequest):
    """
    参数设置请求
    """
    current_timestamp: str = Field(
        ...,
        examples=["2021-01-01 00:00:00"],
        description="当前时间戳 YYYY-MM-DD hh:mm:ss"
    )
    predict_time_length: str = Field(
        ...,
        examples=["10min"],
        description="预测时间长度"
    )
    thresholds: List[float] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="阈值列表",
        examples=[0.1, 0.3, 0.5, 0.7, 0.9]
    )
    models: List[int] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="模型启用状态 [mixed, heart, video]",
        examples=[1, 1, 1]
    )

    @field_validator("current_timestamp")
    def validate_timestamp(cls, value):
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("Invalid timestamp format")
        return value


class HeartDataRequest(BaseRequest):
    """
    心率数据请求
    """
    heart_rate: List[HeartRateDto]


class VideoUploadRequest(BaseRequest):
    """
    视频上传请求
    """
    session_id: str = Field(..., description="会话ID")
    frame_id: int = Field(..., ge=0, description="帧ID")
    timestamp: str = Field(
        ...,
        examples=["2021-01-01 00:00:00"],
        description="时间戳 YYYY-MM-DD hh:mm:ss"
    )
    format: str = Field(
        default="jpg",
        examples=["jpg", "png", "jpeg"],
        description="帧格式"
    )
    file: UploadFile = Field(..., description="视频帧文件")

    @field_validator("timestamp")
    def validate_timestamp(cls, value):
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("Invalid timestamp format")
        return value


class UserDataRequest(BaseRequest):
    """
    用户数据请求
    """
    data: UserDataDto


class BioDataRequest(BaseRequest):
    """
    生化数据请求
    """
    data: List[BioValueDto]


class PredictRequest(BaseRequest):
    """
    预测请求
    """
    session_id: str = Field(..., description="会话ID")
    user_ids: List[str] = Field(
        ...,
        description="用户ID列表",
        examples=["0001", "0002"]
    )