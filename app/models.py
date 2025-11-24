from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum


class Gender(int, Enum):
    MALE = 0
    FEMALE = 1


class PredictStatus(str, Enum):
    LEVEL_1 = "1"
    LEVEL_2 = "2"
    LEVEL_3 = "3"
    LEVEL_4 = "4"
    LEVEL_5 = "5"
    LEVEL_6 = "6"


class UserIdRequest(BaseModel):
    user_id: str = Field(..., examples=["0001", "0002"], description="用户ID")


class BaseData(BaseModel):
    user_id: str = Field(..., examples=["0001"], description="用户ID")


class SetPredictParamsRequest(BaseModel):
    current_timestamp: str = Field(..., examples=["2021-01-01 00:00:00"], description="当前时间戳 YYYY-MM-DD hh:mm:ss")
    predict_time_length: str = Field(..., examples=["10min"], description="预测时间长度")
    thresholds: List[float] = Field(..., min_length=5, max_length=5, description="阈值列表",
                                    examples=[0.1, 0.3, 0.5, 0.7, 0.9])
    models: List[int] = Field(..., min_length=3, max_length=3, description="模型启用状态 [mixed, heart, video]",
                              examples=[1, 1, 1])


class PredictByUserIdRequest(BaseModel):
    """

    """
    user_ids: List[str] = Field(..., description="用户ID列表", examples=["0001", "0002"])
    thresholds: List[float] = Field(..., min_length=5, max_length=5, description="阈值列表",
                                    examples=[0.1, 0.3, 0.5, 0.7, 0.9])
    models: List[int] = Field(..., min_length=3, max_length=3, description="模型启用状态 [mixed, heart, video]",
                              examples=[1, 1, 1])


class HeartRateData(BaseModel):
    """
    心率数据
    """
    rate_id: int = Field(..., description="心率数据ID")
    timestamp: str = Field(..., examples=["2021-01-01 00:00:00"], description="时间戳 YYYY-MM-DD hh:mm:ss")
    value: float = Field(..., ge=0, le=200, description="心率值")

    @field_validator("timestamp")
    def validate_timestamp(cls, value):
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("Invalid timestamp format")
        return value


class HeartDataRequest(UserIdRequest):
    heart_rate: List[HeartRateData]


class FrameData(BaseModel):
    """
    视频帧数据
    """
    frame_id: int
    timestamp: str = Field(..., examples=["2021-01-01 00:00:00"], description="时间戳 YYYY-MM-DD hh:mm:ss")
    format: str = Field(..., examples=["jpeg"], description="图片格式")
    data: str = Field(..., description="图片数据 base64 编码")


class VideoDataRequest(UserIdRequest):
    frames: List[FrameData]


class TaskData(BaseModel):
    """
    管制任务数据
    """
    task_id: int
    task: str = Field(..., examples=["task1"], description="任务名称")
    timestamp: str = Field(..., examples=["2021-01-01 00:00:00"], description="时间戳 YYYY-MM-DD hh:mm:ss")


class UserDataRequest(UserIdRequest):
    """
    用户数据
    """
    age: int
    gender: Gender = Field(..., description="性别")
    occupation: str = Field(..., examples=["xxx"], description="职位")
    tasks: List[TaskData] = Field(..., description="任务列表")
    otherInfo: str = Field(..., description="其他信息")


class BioValue(BaseModel):
    """
    生化数据
    """
    timestamp: str = Field(..., examples=["2021-01-01 00:00:00"], description="时间戳 YYYY-MM-DD hh:mm:ss")
    value_1: Optional[float] = None
    value_2: Optional[float] = None


class BioDataRequest(UserIdRequest):
    data: List[BioValue]


class PredictResult(BaseModel):
    """
    预测结果
    """
    user_id: str
    predict_mixed: Optional[float] = Field(None, ge=0.0, le=1.0, description="混合数据预测结果")
    predict_heart: Optional[float] = Field(None, ge=0.0, le=1.0, description="心率数据预测结果")
    predict_video: Optional[float] = Field(None, ge=0.0, le=1.0, description="视频数据预测结果")
    predict_stats: str = Field(..., description="预测结果状态", examples=["1", "2", "3", "4", "5", "6"])
    timestamp: str = Field(..., examples=["2021-01-01 00:00:00"], description="时间戳 YYYY-MM-DD hh:mm:ss")


class PredictResponse(BaseModel):
    result: List[PredictResult]


class PredictAllResponse(PredictResponse):
    pass


class PredictByUserIdResponse(PredictResponse):
    pass


class GenericResponse(BaseModel):
    code: int = 200
    message: str = Field(default="success")


class HeartDataResponse(GenericResponse):
    message: str = Field(default="heart data upload successfully.")


class VideoDataResponse(GenericResponse):
    message: str = Field(default="video data upload successfully.")


class UserDataResponse(GenericResponse):
    message: str = Field(default="user data upload successfully.")


class BioDataResponse(GenericResponse):
    message: str = Field(default="bio data upload successfully.")


