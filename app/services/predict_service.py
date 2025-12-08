from datetime import datetime
from typing import (
    Optional,
    Dict,
    Any,
    List, Tuple
)

from app.model.video_predict import VideoFatiguePredictor
from app.utils.logger import log
from app.services.storage_service import StorageService
from app.config.base_config import settings
from app.models.dto import PredictResultDto
import torch
from app.model.heart_predict import HeartPredictor


class ModelInterface:
    """
    Interface for prediction models
    """

    @staticmethod
    async def predict_mixed(user_id: str) -> Optional[float]:
        """
        mixed model predict interface
        :param data:
        :return:
        """
        log.info(f"mixed model predict - user : {user_id}")
        try:
            predict_heart = await ModelInterface.predict_heart(user_id)
            predict_video = await ModelInterface.predict_video(user_id)
            prediction = (predict_heart + predict_video) / 2
            log.debug(f"mixed model result: {prediction}")
            return prediction
        except Exception as e:
            log.error(f"mixed model error: {e}")

    @staticmethod
    async def predict_heart(user_id: str) -> Optional[float]:
        """
        Heart Model Predict Interface
        :param user_id:
        :return:
        """
        log.info(f"heart model predict - user : {user_id}")
        data = await StorageService.get_heart_data(user_id)

        try:
            if data is None:
                log.error("heart model error: no heart data")
                return None

            predictor = HeartPredictor('app/weights/best_temporal_heart_CNN.pth')

            if not predictor.model:
                log.error("heart model error: no model")
                return None

            input_tensor = predictor.preprocess_data(data, sampling_rate=1)

            if input_tensor is None:
                log.error("heart model error: no preprocess data")
                return None

            with torch.no_grad():
                result = predictor.model(input_tensor)
                probabilities = torch.softmax(result, dim=1)
                fatigue_probability = probabilities[0, 1].item()
                log.debug(f"heart model result: {fatigue_probability}")
                return float(fatigue_probability)
        except Exception as e:
            log.error(f"heart model error: {e}")
            return None

    @staticmethod
    async def predict_video(user_id: str) -> Tuple[Optional[float], int]:
        """
        Video Model Predict Interface
        :param user_id:
        :return:
        """
        log.info(f"video model predict - user : {user_id}")
        get = StorageService()
        frames = await get.get_video_data(user_id)
        try:
            # 实例化视频预测器，使用占位符路径
            predictor = VideoFatiguePredictor(model_path='app/weights/video_fatigue_model.pth')

            # 调用预测方法。注意：这里我们传入 None，让预测器返回模拟值进行测试
            fatigue_probability, fatigue_status = predictor.predict_fatigue(user_id, frames_data=frames)

            log.debug(f"video model result: {fatigue_probability}")
            return fatigue_probability, fatigue_status
        except Exception as e:
            log.error(f"video model error: {e}")
            return 0.0, 0

    @staticmethod
    async def get_predict_status(prediction: float) -> str:
        """
        :param user_id:
        :return:
        """
        try:
            log.info(f"get predict status - prediction : {prediction}")
            if prediction is None or prediction > 1 or prediction < 0:
                return "0"
            for idx, threshold in enumerate(settings.DEFAULT_THRESHOLDS):
                if prediction < threshold:
                    log.info(f"get predict status - status : {idx + 1}")
                    return f"{idx + 1}"
        except Exception as e:
            log.error(f"get predict status error: {e}")

    @staticmethod
    async def predict(user_ids: List[str]) -> List[PredictResultDto]:
        """

        :param user_ids:
        :return:
        """
        results = []
        for user_id in user_ids:
            mixed = 0.0
            heart = 0.0
            video = 0.0
            fatigue_status = 0
            if settings.DEFAULT_MODELS[0]:
                mixed = await ModelInterface.predict_mixed(user_id)
            if settings.DEFAULT_MODELS[1]:
                heart = await ModelInterface.predict_heart(user_id)
            if settings.DEFAULT_MODELS[2]:
                video, fatigue_status = await ModelInterface.predict_video(user_id)

            result_dto = PredictResultDto(
                predict_mixed=mixed,
                predict_heart=heart,
                predict_video=video,
                predict_stats=await ModelInterface.get_predict_status(prediction=mixed),
                fatigue_status=fatigue_status,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            results.append(result_dto.to_dict(user_id))
        return results
