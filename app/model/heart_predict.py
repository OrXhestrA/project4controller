import os
import numpy as np
import torch
import torch.nn as nn
from typing import (
    Dict,
    Any,
    Optional
)
from app.config.base_config import settings
from app.utils.logger import log
import asyncio


class HeartPredictor:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.seq_len = 9600
        self.required_min_points = 300

        self._load_model()

    def _load_model(self):
        """
        加载训练好的模型
        :return:
        """
        try:
            if not os.path.exists(self.model_path):
                log.error(f"Model file not found - path : {self.model_path}")
                return

            class TemporalCNN(nn.Module):
                def __init__(self, input_length=9600, num_classes=2, dropout=0.3):
                    super(TemporalCNN, self).__init__()
                    filter_sizes = [5, 15, 31]
                    num_filters = 64
                    hidden_units = 128

                    self.conv_layers = nn.ModuleList()
                    for filter_size in filter_sizes:
                        padding = filter_size // 2
                        self.conv_layers.append(
                            nn.Sequential(
                                nn.Conv1d(
                                    1,
                                    num_filters,
                                    kernel_size=filter_size,
                                    padding=padding
                                ),
                                nn.BatchNorm1d(num_filters),
                                nn.ReLU(),
                                nn.MaxPool1d(4),
                                nn.Dropout(dropout)
                            )
                        )

                    self.feature_fusion = nn.Sequential(
                        nn.Conv1d(num_filters * len(filter_sizes), hidden_units, kernel_size=3, padding=1),
                        nn.BatchNorm1d(hidden_units),
                        nn.ReLU(),
                        nn.MaxPool1d(2),
                        nn.Dropout(dropout),

                        nn.Conv1d(hidden_units, hidden_units * 2, kernel_size=3, padding=1),
                        nn.BatchNorm1d(hidden_units * 2),
                        nn.ReLU(),
                        nn.AdaptiveAvgPool1d(1),
                        nn.Dropout(dropout)
                    )

                    self.classifier = nn.Sequential(
                        nn.Linear(hidden_units * 2, hidden_units),
                        nn.ReLU(),
                        nn.Dropout(dropout),
                        nn.Linear(hidden_units, num_classes)
                    )

                def forward(self, x):
                    x = x.transpose(1, 2)
                    features = []
                    for conv_layer in self.conv_layers:
                        feature = conv_layer(x)
                        features.append(feature)

                    target_length = min([f.shape[2] for f in features])
                    for i in range(len(features)):
                        if features[i].size(2) != target_length:
                            features[i] = nn.AdaptiveAvgPool1d(target_length)(features[i])

                    x = torch.cat(features, dim=1)
                    x = self.feature_fusion(x)
                    x = x.view(x.size(0), -1)
                    x = self.classifier(x)
                    return x

            self.model = TemporalCNN(input_length=self.seq_len)

            if torch.cuda.is_available():
                checkpoint = torch.load(self.model_path)
            else:
                checkpoint = torch.load(self.model_path, map_location=torch.device('cpu'))

            if 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model.load_state_dict(checkpoint)

            self.model.eval()
            log.info(f"Load model success - path : {self.model_path}")
        except Exception as e:
            log.error(f"Load model error - path : {self.model_path} - error : {e}")
            self.model = None

    def _resample_data(self, data: list, original_rate: int, target_rate: int = 32) -> np.ndarray:
        if original_rate == target_rate:
            return np.array(data)

        original_length = len(data)
        target_length = int(original_length * target_rate / original_rate)

        original_time = np.linspace(0, original_length / original_rate, original_length)
        target_time = np.linspace(0, original_length / original_rate, target_length)

        resampled_data = np.interp(target_time, original_time, data)
        log.info(f"Resample data success - original_rate : {original_rate} - target_rate : {target_rate}")
        return resampled_data

    def preprocess_data(self, data: list, sampling_rate: int = 1) -> Optional[torch.Tensor]:
        try:
            data = np.array(data, dtype=np.float32)

            if len(data) == 0:
                log.warning("Data is empty")
                return None

            if len(data) < self.required_min_points:
                log.warning(f"Data length is too short - required_min_points : {self.required_min_points}")
                return None

            valid_mask = (data >= 30) & (data <= 200)
            if not np.all(valid_mask):
                invalid_count = np.sum(~valid_mask)
                log.warning(f"Invalid data points found - count : {invalid_count}")

                from scipy import ndimage
                data[~valid_mask] = np.nan
                data = ndimage.generic_filter(data, np.nanmean, size=3, mode='nearest')

            if sampling_rate != 32:
                data = self._resample_data(data.tolist(), sampling_rate, 32)

            data_normalized = (data - np.mean(data)) / (np.std(data) + 1e-8)
            if len(data_normalized) < self.seq_len:
                padding = np.zeros(self.seq_len - len(data_normalized))
                data_normalized = np.concatenate([data_normalized, padding])
            elif len(data_normalized) > self.seq_len:
                data_normalized = data_normalized[-self.seq_len:]

            input_tensor = torch.FloatTensor(data_normalized).unsqueeze(0).unsqueeze(-1)

            return input_tensor

        except Exception as e:
            log.error(f"Preprocess data error - error : {e}")
            return None
