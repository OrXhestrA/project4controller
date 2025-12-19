import asyncio
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
from app.config.base_config import settings

class ModelInterface:
    """
    Interface for prediction models
    """

    @staticmethod
    async def predict_mixed(predict_heart: float, predict_video: float) -> Optional[float]:
        """
        mixed model predict interface
        :param predict_heart:
        :param predict_video:
        :return:
        """
        try:
            prediction = (settings.DEFAULT_COEFFICIENT * predict_heart + (1 - settings.DEFAULT_COEFFICIENT) * predict_video)
            log.debug(f"mixed model result: {prediction}")
            return round(float(prediction), 3)
        except Exception as e:
            log.error(f"mixed model error: {e}")

    @staticmethod
    async def predict_heart(user_id: str):
        """
        Heart Model Predict Interface
        :param data:
        :param user_id:
        :return:
        """
        log.info(f"heart model predict - user : {user_id}")
        data = await StorageService.get_heart_data(user_id)

        try:
            if data is None:
                log.warning("heart model error: no heart data")
                return [], 0.0

            predictor = HeartPredictor('app/weights/best_temporal_heart_CNN.pth')
            # predictor = HeartPredictor('Z:\\2025\\code\\heartDemo\\app\\weights\\best_temporal_heart_CNN.pth')
            if not predictor.model:
                log.warning("heart model error: no model")
                return [], 0.0

            num_segment = int(len(data) / 30)
            if num_segment < 1:
                log.warning("heart model error: no enough data")
                return [], 0.0

            segments = HeartPredictor.segment_data(data,
                                                   segment_length=150,
                                                   num_segments=num_segment,
                                                   fill_value=70
                                                   )
            weights = HeartPredictor.calculate_weights(num_segment, 'exponential')
            results = []
            final_result = 0

            for segment, weight in zip(segments, weights):
                input_tensor = predictor.preprocess_data(segment, sampling_rate=1)

                if input_tensor is None:
                    log.warning("heart model error: no preprocess data")
                    results.append(0.0)
                log.info(f"segment: {segment}")
                with torch.no_grad():
                    result = predictor.model(input_tensor)
                    probabilities = torch.softmax(result, dim=1)
                    fatigue_probability = probabilities[0, 1].item()
                    log.info(f"segment result: {fatigue_probability}")
                    results.append(fatigue_probability)
                    final_result += fatigue_probability * weight
            results = [round(result, 3) for result in results]
            final_result = round(final_result, 3)
            log.info(f"heart model result: {final_result}")
            return results, float(final_result)
        except Exception as e:
            log.error(f"heart model error: {e}")
            return [], 0.0

    @staticmethod
    async def predict_video(user_id: str):
        """
        Video Model Predict Interface
        :param user_id:
        :return:
        """
        log.info(f"video model predict - user : {user_id}")
        get = StorageService()
        frames = await get.get_video_data(user_id)
        if frames is None:
            log.warning("video model error: no video data")
            return [], 0.0, 0
        try:
            # 实例化视频预测器，使用占位符路径
            predictor = VideoFatiguePredictor(model_path='app/weights/video_fatigue_model.pth')

            # 调用预测方法。注意：这里我们传入 None，让预测器返回模拟值进行测试
            results, final_result, final_status = predictor.predict_fatigue(user_id, frames_data=frames)

            return results, float(final_result), final_status
        except Exception as e:
            log.error(f"video model error: {e}")
            return [], 0.0, 0

    @staticmethod
    async def get_predict_status(prediction: float) -> str:
        """
        :param prediction:
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
            heart_results = []
            video_results = []
            video_status = 0

            if settings.DEFAULT_MODELS[1]:
                heart_results, heart = await ModelInterface.predict_heart(user_id)
            if settings.DEFAULT_MODELS[2]:
                video_results, video, video_status = await ModelInterface.predict_video(user_id)
            if settings.DEFAULT_MODELS[0]:
                mixed = await ModelInterface.predict_mixed(heart, video)
            log.info(f"mixed model result: {mixed}, heart: {heart}, video: {video}")
            result_dto = PredictResultDto(
                predict_mixed=mixed,
                predict_heart=heart,
                predict_heart_list=heart_results,
                predict_video_list=video_results,
                predict_video=video,
                predict_stats=await ModelInterface.get_predict_status(prediction=mixed),
                video_predict_stats=video_status,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            results.append(result_dto.to_dict(user_id))
        return results


# async def example_usage():
#     """使用示例"""
#     # 模拟用户数据
#     user_data = [50, 71, 50, 61, 65, 53, 52, 50, 67, 60] * 10  # 300个点
#     log.info(f"user data: {len(user_data)}")
#     # 进行预测
#     final_result, results = await ModelInterface.predict_heart(user_id="", data=user_data)
#
#     if final_result is not None:
#         print(f"最终结果: {final_result:.3f}")
#         print(f"最终结果: {final_result}")
#         print("结果:", results)
#
#
# # 测试代码
# if __name__ == "__main__":
#     # 运行示例
#     asyncio.run(example_usage())
