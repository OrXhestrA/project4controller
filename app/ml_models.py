from typing import Optional, Dict, Any, List
from app.utils import log
import torch


class ModelInterface:
    """
    Interface for prediction models
    """

    @staticmethod
    async def predict_mixed(user_data: Dict[str, Any]) -> Optional[float]:
        """
        mixed model predict interface
        # TODO load model
            import torch
            model = torch.load('model.pth')
            model.eval()
            with torch.no_grad():
                result = model(preprocessed_data)
            return float(result)
        :param user_data:
        :return:
        """
        user_id = user_data.get('user_id', 'unknown')
        log.info(f"mixed model predict - user : {user_id}")

        prediction = 0.1
        log.debug(f"mixed model result: {prediction}")
        return prediction

    @staticmethod
    async def predict_heart(user_data: Dict[str, Any]) -> Optional[float]:
        """
        Heart Model Predict Interface

        # TODO heart model
        :param user_data:
        :return:
        """
        user_id = user_data.get('user_id', 'unknown')
        log.info(f"heart model predict - user : {user_id}")

        try:
            heart_data = user_data.get('heart_data', [])
            if heart_data is None:
                log.error("heart model error: no heart data")
                return None
            if len(heart_data) < 300:
                log.error("heart model error: not enough heart data")
                return None

            # load model
            model = torch.load('model.pth')
            model.eval()

            preprocessed_data = torch.FloatTensor(heart_data).unsqueeze(0).unsqueeze(-1)

            with torch.no_grad():
                result = model(preprocessed_data)
                prediction = float(result)
                log.debug(f"heart model result: {prediction}")
                return prediction
        except Exception as e:
            log.error(f"heart model error: {e}")
            return None


    @staticmethod
    async def predict_video(user_data: Dict[str, Any]) -> Optional[float]:
        """
        Video Model Predict Interface

        # TODO video model
        :param user_data:
        :return:
        """
        user_id = user_data.get('user_id', 'unknown')
        log.info(f"video model predict - user : {user_id}")

        prediction = 0.1
        log.debug(f"video model result: {prediction}")
        return prediction

    @staticmethod
    def get_predict_status(predictions: dict, thresholds: list) -> str:
        """
        # TODO create predict status
        :param predictions:
        :param thresholds:
        :return:
        """
        value = predictions.get("mixed")
        if value is None:
            available_values = [v for v in predictions.values() if v is not None]
            if not available_values:
                return "normal"
            value = sum(available_values) / len(available_values)

        for i, threshold in enumerate(thresholds):
            if value < threshold:
                return str(i + 1)
        return "normal"


ml_models = ModelInterface()