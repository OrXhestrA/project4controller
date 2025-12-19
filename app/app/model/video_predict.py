# project4controller/app/model/video_predict.py

from typing import Optional, Tuple, List
from app.utils.logger import log
import numpy as np
from scipy.spatial import distance as dist
import cv2
import mediapipe as mp
import random
import os
from collections import deque

mp_face_mesh = mp.solutions.face_mesh

# 初始化 MediaPipe Face Mesh 静态实例
FACE_MESH = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# 核心眼睛/嘴巴关键点索引定义
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
LEFT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH = [61, 291, 0, 17]

# 阈值配置
EYE_AR_THRESH = 0.18
MAR_THRESH = 0.60


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
    return A / (C + 1e-6)


class FatigueTrendAnalyzer:
    """
    负责分析长周期的疲劳趋势（基于EAR基准值衰减）。
    """

    def __init__(self, window_size=30):
        self.ear_history = deque(maxlen=window_size)
        self.baseline_ear = None
        self.CALIBRATION_FRAMES = 10
        self.yawn_history = deque(maxlen=window_size)

    def update(self, current_ear, current_mar) -> int:
        """
        更新状态并返回预警等级。
        Return: 0(正常), 1(轻度预警-建议休息), 2(重度预警-危险)
        """
        self.ear_history.append(current_ear)
        is_yawning = 1 if current_mar > MAR_THRESH else 0
        self.yawn_history.append(is_yawning)

        # 1. 动态基准校准
        if self.baseline_ear is None:
            if len(self.ear_history) >= self.CALIBRATION_FRAMES:
                self.baseline_ear = np.mean(self.ear_history)
                log.info(f"[Calibration] 用户基准睁眼度已确立: {self.baseline_ear:.4f}")
            return 0

        # 2. 计算当前窗口的平均状态
        current_avg_ear = np.mean(self.ear_history)
        decay_ratio = current_avg_ear / (self.baseline_ear + 1e-6)

        is_eyes_dropping = decay_ratio < 0.85
        is_eyes_dropping_heavy = decay_ratio < 0.5
        is_freq_yawning = sum(self.yawn_history) >= 2

        # 3. 判定预警等级
        warning_level = 0
        if is_eyes_dropping:
            warning_level = 1
        if is_freq_yawning:
            warning_level = 2 if warning_level == 1 else 1
        if is_eyes_dropping_heavy:
            warning_level = 2

        return warning_level


# =======================================================
# 核心预测器类
# =======================================================

class VideoFatiguePredictor:
    """
    视频疲劳预测接口 (MediaPipe + 能量槽 + PERCLOS)
    """

    def __init__(self, model_path: str):
        self.model_path = model_path
        log.info("Video model logic (MediaPipe) initialized.")
        self.face_mesh = FACE_MESH
        self.is_ready = True

    def _calculate_ear_mar_on_frame(self, frame: np.ndarray) -> Tuple[float, float]:
        """内部 MediaPipe 处理函数: 返回 (EAR, MAR)"""
        ear, mar = 0.0, 0.0
        if frame is None:
            return ear, mar

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

    def predict_fatigue(self, user_id: str, frames_data: list) -> Tuple[Optional[float], int]:
        """
        核心预测逻辑：对用户返回基于视频分析的疲劳预测概率 (0.0 - 1.0) 和 预警等级 (0-2)。

        Args:
            user_id: 用户ID
            frames_data: 图片二进制数据列表 (List[bytes])
        """
        log.debug(f"Starting video fatigue prediction for {user_id}")

        if not frames_data:
            log.warning(f"No frame data provided for {user_id}. Returning default.")
            return 0.0, 0

        # --- 初始化：轨道一 (原有 TrendAnalyzer) ---
        trend_analyzer = FatigueTrendAnalyzer(window_size=20)
        max_warning_level = 0

        curr_closed_seq = 0
        max_closed_seq = 0

        # --- PERCLOS 统计变量 ---
        total_closed_frames = 0
        valid_frame_count = 0

        # --- 初始化：轨道二 (能量槽评分) ---
        MAX_ENERGY = 100.0
        current_energy = 90.0
        min_energy_recorded = 100.0

        # 能量参数 (针对 2秒/帧 优化)
        PENALTY_EYE_CLOSED = 20.0
        PENALTY_YAWN = 10.0
        RECOVERY_NORMAL = 5.0

        try:
            for frame_bytes in frames_data:
                # 1. 解码图像
                try:
                    nparr = np.frombuffer(frame_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                except Exception:
                    continue

                if frame is None:
                    continue

                valid_frame_count += 1
                ear, mar = self._calculate_ear_mar_on_frame(frame)

                # 2. 状态判定
                is_eye_closed = ear < EYE_AR_THRESH
                is_yawning = mar > MAR_THRESH

                # --- 轨道一：预警逻辑更新 ---
                if is_eye_closed:
                    total_closed_frames += 1
                    curr_closed_seq += 1
                else:
                    max_closed_seq = max(max_closed_seq, curr_closed_seq)
                    curr_closed_seq = 0

                current_warning = trend_analyzer.update(ear, mar)
                max_warning_level = max(max_warning_level, current_warning)

                # --- 轨道二：能量槽更新 ---
                if is_eye_closed:
                    current_energy -= PENALTY_EYE_CLOSED
                    if curr_closed_seq >= 2:
                        current_energy -= 10.0  # 连续闭眼额外惩罚
                elif is_yawning:
                    current_energy -= PENALTY_YAWN
                else:
                    current_energy += RECOVERY_NORMAL

                # 能量边界限制
                current_energy = max(0.0, min(current_energy, MAX_ENERGY))
                if current_energy < min_energy_recorded:
                    min_energy_recorded = current_energy

            # 循环结束结算
            max_closed_seq = max(max_closed_seq, curr_closed_seq)

            if valid_frame_count == 0:
                return 0.0, 0

            # ==========================================
            # 最终结算：多维度融合
            # ==========================================

            # A. 能量得分 (能量越低分越高)
            energy_score = (100.0 - min_energy_recorded) / 100.0

            # B. PERCLOS 得分
            perclos = total_closed_frames / valid_frame_count
            perclos_score = 0.0

            if perclos >= 0.3:
                perclos_score = 0.8 + (perclos - 0.3)
            elif perclos >= 0.15:
                perclos_score = 0.4 + ((perclos - 0.15) / 0.15) * 0.4
            else:
                perclos_score = perclos * 2.0

            # C. 融合分数 (取最大值)
            raw_score = max(energy_score, perclos_score)

            # D. 预警等级对齐 (Sanity Check)
            final_warning_level = max_warning_level
            if max_closed_seq >= 2:
                final_warning_level = 2
                log.warning(f"触发硬规则：连续 {max_closed_seq} 帧闭眼")

            final_score = raw_score


            # 封顶保底
            final_score = min(final_score, 0.99)
            final_score = max(final_score, 0.05)

            log.info(f"PERCLOS: {perclos:.2f} | MinEnergy: {min_energy_recorded:.1f}")
            log.info(f"Video Predict >> Level: {final_warning_level}, Score: {final_score:.2f}")

            return final_score, final_warning_level

        except Exception as e:
            log.error(f"Video model processing failed for {user_id}: {e}")
            return 0.0, 0

    # def predict_fatigue_from_paths(self, user_id: str, file_paths: list) -> Tuple[float, int]:
    #     """
    #     工具方法：从文件路径读取图片并预测 (方便本地调试)
    #     """
    #     frames_data = []
    #     for path in sorted(file_paths):
    #         try:
    #             with open(path, "rb") as f:
    #                 frames_data.append(f.read())
    #         except Exception:
    #             continue
    #
    #     return self.predict_fatigue(user_id, frames_data)


# def get_all_image_paths(folder_path):
#     valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
#     image_path_list = []
#     for root, dirs, files in os.walk(folder_path):
#         for file in files:
#             if file.lower().endswith(valid_extensions):
#                 full_path = os.path.join(root, file)
#                 full_path = full_path.replace('\\', '/')
#                 image_path_list.append(full_path)
#     return image_path_list
#
#
# if __name__ == "__main__":
#     # 本地测试入口
#     frame_dir = r"C:\Users\ROG\Desktop\output_frames"
#     frames = get_all_image_paths(frame_dir)
#     predictor = VideoFatiguePredictor("1")
#
#     score, level = predictor.predict_fatigue_from_paths('001', frames)
#     print(f"Test Result -> Score: {score}, Level: {level}")