from datetime import datetime
from typing import List, Dict, Any
from app.models import (
    HeartDataResponse, HeartDataRequest,
    VideoDataResponse, FrameData,
    UserDataResponse, UserDataRequest, TaskData, Gender,
    BioDataResponse, BioDataRequest, BioValue,
    PredictResult,
    PredictByUserIdResponse, PredictAllResponse, GenericResponse, VideoDataRequest
)
from app.ml_models import ml_models
from app.config import settings
from app.utils import log
from app.database import get_db, get_redis_pool
from app.cache_aside_repository import CacheAsideRepository


PREDICT_PARAMS = {
    "thresholds": [0.1, 0.3, 0.5, 0.7, 0.9],
    "models": [1, 1, 1]  # [mixed, heart, video]
}


class DataService:
    """Manage Data Getter"""
    def __init__(self):
        self.mock_data_cache: Dict[str, Any] = {}

    @staticmethod
    async def upload_heart_data(request: HeartDataRequest) -> HeartDataResponse:
        log.info(f"uploading heart data from user {request.user_id}")

        # TODO get from db or interface
        # Example: data = await db.insert(HeartData)
        # Example: data = await interface

        # data stored in db or cache for now
        async for db in get_db():
            redis_client = await get_redis_pool()
            repo = CacheAsideRepository(db, redis_client)

            try:
                heart_data_list = [hd.dict() for hd in request.heart_rate]
                await repo.insert_heart_rate_data(request.user_id, heart_data_list)

                return HeartDataResponse()
            except Exception as e:
                log.error(f"error when insert heart rate data: {e}")

    @staticmethod
    async def upload_video_data(self, request: VideoDataRequest) -> VideoDataResponse:
        log.info(f"uploading video data from user {request.user_id}")
        # TODO get from db or interface
        # Example: data = await db.insert(VideoData)
        # Example: data = await interface

        # data stored in db or cache for now
        async for db in get_db():
            redis_client = await get_redis_pool()
            repo = CacheAsideRepository(db, redis_client)

            try:
                video_data_list = [vd.dict() for vd in request.frames]
                await repo.insert_video_data(request.user_id, video_data_list)
                return VideoDataResponse()
            except Exception as e:
                log.error(f"error when insert video data: {e}")
                return VideoDataResponse(code=500, message="internal server error")

    @staticmethod
    async def upload_user_data(self, request: UserDataRequest) -> UserDataResponse:
        log.info(f"uploading user data {request.user_id}")
        # TODO get from db or interface
        # Example: data = await db.insert(UserData)
        # Example: data = await interface

        # data stored in db or cache for now
        async for db in get_db():
            redis_client = await get_redis_pool()
            repo = CacheAsideRepository(db, redis_client)

            try:
                task_data = [task.dict() for task in request.tasks]
                await repo.insert_user_data(request.user_id, request)
                await repo.insert_task_data(request.user_id, task_data)
                return UserDataResponse()
            except Exception as e:
                log.error(f"error when insert user data: {e}")
                return UserDataResponse(code=500, message="internal server error")

    @staticmethod
    async def upload_bio_data(self, request: BioDataRequest) -> BioDataResponse:
        log.info(f"uploading bio data from user {request.user_id}")
        # TODO get from db or interface
        # Example: data = await db.insert(BioData)
        # Example: data = await interface

        # data stored in db or cache for now
        async for db in get_db():
            redis_client = await get_redis_pool()
            repo = CacheAsideRepository(db, redis_client)

            try:
                await repo.insert_bio_data(request.user_id, request)
                return BioDataResponse()
            except Exception as e:
                log.error(f"error when insert bio data: {e}")
                return BioDataResponse(code=500, message="internal server error")
        return BioDataResponse()


class PredictService:
    """Manage Predict Service"""
    def __init__(self):
        self.predict_params = {
            "current_time": datetime.now().strftime("%y-%m-%d %H:%M:%S"),
            "predict_time_length": settings.DEFAULT_PREDICT_TIME_LENGTH,
            "thresholds": settings.DEFAULT_THRESHOLDS.copy(),
            "models": settings.DEFAULT_MODELS.copy()
        }

    def set_predict_params(self, params: Dict[str, Any]) -> GenericResponse:
        """Set Parameters Storage"""
        self.predict_params.update(params)
        log.info(f"predict params updated: {self.predict_params}")

    async def predict_for_user(
            self,
            user_id: str,
            thresholds: List[float] = None,
            models: List[int] = None
    ) -> PredictResult:
        """

        :param user_id:
        :param thresholds:
        :param models:
        :return:
        """
        thresholds = thresholds or self.predict_params["thresholds"]
        models = models or self.predict_params["models"]

        log.info(f"predict for user {user_id}, use model {models}")

        # TODO get data and process data
        user_data = {"user_id": user_id}
        predictions = {}

        if models[0]:
            predictions["mixed"] = await ml_models.predict_mixed(user_data)
        if models[1]:
            predictions["heart"] = await ml_models.predict_heart(user_data)
        if models[2]:
            predictions["video"] = await ml_models.predict_video(user_data)

        status = ml_models.get_predict_status(predictions, thresholds)

        result = PredictResult(
            user_id=user_id,
            predict_mixed=predictions.get("mixed"),
            predict_heart=predictions.get("heart"),
            predict_video=predictions.get("video"),
            predict_stats=status,
            timestamp=datetime.now().strftime("%y-%m-%d %H:%M:%S")
        )
        log.info(f"predict result: {result}")
        return result

    async def predict_all(self) -> PredictAllResponse:
        """

        :return:
        """
        log.info("predict all users.")
        # TODO get all activated users
        # Example: user_ids = await db.get_all_activated_users()

        user_ids = ["0001", "0002"]

        results = []
        for user_id in user_ids:
            result = await self.predict_for_user(user_id)
            results.append(result)

        log.info(f"predict all results: {len(results)}")
        return PredictAllResponse(result=results)

    async def predict_by_user_ids(
            self,
            user_ids: List[str],
            thresholds: List[float],
            models: List[int]
    ) -> PredictByUserIdResponse:
        """
        :param models:
        :param thresholds:
        :param user_ids:
        :return:
        """
        log.info(f"predict by user ids: sum {len(user_ids)}")
        results = []
        for user_id in user_ids:
            result = await self.predict_for_user(user_id, thresholds, models)
            results.append(result)

        return PredictByUserIdResponse(result=results)


data_service = DataService()
predict_service = PredictService()