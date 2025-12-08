from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    field_validator
)
from typing import (
    List, Optional
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
    predict_time_length: Optional[int] = Field(
        None,
        description="预测时间长度"
    )
    thresholds: List[float] = Field(
        None,
        min_length=5,
        max_length=5,
        description="阈值列表",
        examples=[[0.1, 0.3, 0.5, 0.7, 0.9]]
    )
    models: List[int] = Field(
        None,
        min_length=3,
        max_length=3,
        description="模型启用状态 [mixed, heart, video]",
        examples=[[1, 1, 1]]
    )


class HeartDataRequest(BaseRequest):
    """
    心率数据请求
    """
    heart_rate: List[HeartRateDto]


class VideoUploadRequest(BaseRequest):
    """
    视频上传请求
    """
    format: str = Field(
        default="jpg",
        examples=["jpg", "png", "jpeg"],
        description="帧格式"
    )
    file: UploadFile = Field(..., description="视频帧文件")


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
    task_id: str = Field(..., description="任务ID")
    user_ids: List[str] = Field(
        ...,
        description="用户ID列表",
        examples=["0001", "0002"]
    )