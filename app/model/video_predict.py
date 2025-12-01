# project4controller/app/model/video_predict.py

from typing import Optional, Tuple, List
from app.utils.logger import log
import numpy as np
from scipy.spatial import distance as dist
import cv2
import mediapipe as mp
import random

mp_face_mesh = mp.solutions.face_mesh

# 初始化 MediaPipe Face Mesh 静态实例
# 在类外部初始化，保证进程中只创建一次，提高效率
FACE_MESH = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# 核心眼睛/嘴巴关键点索引定义
LEFT_EYE = [33, 160, 158, 133, 144, 163]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH = [61, 291, 0, 17]

# 阈值 (从 yolov5_detect/main.py 提取)
EYE_AR_THRESH = 0.15
MAR_THRESH = 0.65


# =======================================================
# 几何计算函数
# =======================================================

def eye_aspect_ratio(eye: np.ndarray) -> float:
    """计算眼睛长宽比 (EAR)"""
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)


def mouth_aspect_ratio(mouth: np.ndarray) -> float:
    """计算嘴巴长宽比 (MAR)"""
    A = dist.euclidean(mouth[2], mouth[3])  # 垂直距离
    C = dist.euclidean(mouth[0], mouth[1])  # 水平距离
    # 避免除以零
    return A / (C + 1e-6)


# =======================================================
# 核心预测器类
# =======================================================

class VideoFatiguePredictor:
    """
    视频疲劳预测接口。
    模型权重加载已替换为 MediaPipe 实例初始化，无额外权重文件。
    """
    def __init__(self, model_path: str):
        # 即使 MediaPipe 没有外部权重文件，我们也保留 model_path 参数，以保持接口一致性
        self.model_path = model_path
        log.info("Video model logic (MediaPipe) initialized.")
        self.face_mesh = FACE_MESH
        self.is_ready = True

    def predict_fatigue(self, user_id: str, frames_data: list) -> Optional[float]:
        """
        对用户返回基于视频分析的疲劳预测概率 (0.0 - 1.0)。
        如果未提供 frame_data，则返回模拟的随机预测结果。
        """
        log.debug(f"Starting video fatigue prediction for {user_id}")

        if frames_data is None:
            # ----------------------------------------------------
            # 默认/模拟逻辑 (当没有实际帧数据时使用)
            # ----------------------------------------------------
            log.warning(f"No frame data provided for {user_id}. Returning simulated prediction.")
            # 返回一个介于 0.3 和 0.8 之间的随机值进行测试
            fatigue_probability = random.uniform(0.3, 0.8)
            return fatigue_probability

        # ----------------------------------------------------
        # 实际模型计算逻辑 (需要传入帧数据字节流)
        # ----------------------------------------------------
        try:
            probability = []
            # 1. 解码图像 (将字节流转换为 OpenCV 图像对象)
            for frame_data in frames_data:
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    log.error(f"Failed to decode image data for {user_id}. Data might be corrupted.")
                    return None

                # 2. 运行 MediaPipe 计算 EAR/MAR
                ear, mar = self._calculate_ear_mar_on_frame(frame)

                # 3. 疲劳概率计算（单帧规则）
                # 评估眼睛和嘴巴状态
                is_eye_closed = ear < EYE_AR_THRESH
                is_mouth_open = mar > MAR_THRESH

                # 简单的规则模型：将 EAR/MAR 状态映射到疲劳概率
                if is_eye_closed and is_mouth_open:
                    # 闭眼+打哈欠 = 极度疲劳
                    fatigue_probability = 0.95
                elif is_eye_closed or is_mouth_open:
                    # 闭眼 或 打哈欠 = 中度疲劳
                    fatigue_probability = 0.70
                elif ear > 0.3:
                    # 眼睛睁得很大 = 清醒
                    fatigue_probability = 0.05
                else:
                    # 默认状态
                    fatigue_probability = 0.35
                probability.append(fatigue_probability)
            return sum(probability) / len(probability)

        except Exception as e:
            log.error(f"Video model processing failed for {user_id}: {e}")
            return None

    def _calculate_ear_mar_on_frame(self, frame: np.ndarray) -> Tuple[float, float]:
        """内部 MediaPipe 处理函数"""
        ear, mar = 0.0, 0.0

        # MediaPipe 期望 RGB 格式
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            h, w, _ = frame.shape
            mp_points = np.array([(int(lm.x * w), int(lm.y * h))
                                  for lm in face_landmarks.landmark])

            # 计算 EAR 和 MAR
            avg_ear = (eye_aspect_ratio(mp_points[LEFT_EYE]) + eye_aspect_ratio(mp_points[RIGHT_EYE])) / 2.0
            mar = mouth_aspect_ratio(mp_points[MOUTH])
            return avg_ear, mar

        return ear, mar