from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    field_validator
)
import json
from typing import (
    List,
    Optional
)
from app.models.dto import (
    PredictResultDto,
    VideoFrameInfoDto,
    UserDataDto
)


class GenericResponse(BaseModel):
    """
    通用响应
    """
    code: int = 200
    message: str = Field(default="success")


class HeartDataResponse(GenericResponse):
    """
    心率数据响应
    """
    message: str = Field(default="heart data upload successfully.")


class VideoDataResponse(GenericResponse):
    """
    视频数据响应
    """

    def __init__(self, data: VideoFrameInfoDto):
        message_str = json.dumps(
            data.to_dict(),
            ensure_ascii=False
        )
        super().__init__(message=message_str)


class UserDataResponse(GenericResponse):
    """
    用户数据响应
    """

    def __init__(self, user_data: UserDataDto):
        super().__init__()
        self.message = json.dumps(
            user_data.to_dict(),
            ensure_ascii=False
        )


class BioDataResponse(GenericResponse):
    """
    生化数据响应
    """

    def __init__(self):
        super().__init__()
        self.message = "bio data upload successfully."


class PredictResponse(GenericResponse):
    """
    预测结果响应
    """
    data: str = Field(default=[])
    task_id: str = Field(default="")

    def __init__(self, predict_results: List[PredictResultDto], task_id: str):
        """

        :param predict_results:
        """
        super().__init__()
        self.data = json.dumps(
            [predict_result for predict_result in predict_results],
            ensure_ascii=False
        )
        self.task_id = task_id


class PredictAllResponse(PredictResponse):
    """
    预测所有结果响应
    """
    pass


class PredictByUserIdResponse(PredictResponse):
    """
    预测指定用户结果响应
    """
    pass
