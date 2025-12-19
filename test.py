import requests
import os
import time

# 配置
API_URL = "http://127.0.0.1:8000/api"
USER_ID = "auto_test_user"
# 替换为你切好的图片文件夹路径 (确保里面有 .jpg 图片)
FRAME_DIR = r"C:\Users\ROG\Desktop\output_frames"


# --- 新增：设置系统参数 ---
def set_system_params():
    print(f"0. 配置系统参数 (只启用视频模型)...")
    url = f"{API_URL}/set_params"

    # 这里填入你刚才提供的 JSON
    payload = {
        "user_id": "admin",  # 用于鉴权或记录日志，写 admin 即可
        "current_timestamp": "2025-12-06 12:00:00",
        "predict_time_length": "10min",
        "thresholds": [0.1, 0.3, 0.5, 0.7, 0.9],
        "models": [0, 0, 1]  # <--- 重点：[混合关, 心率关, 视频开]
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("   [OK] 参数设置成功！系统现在只运行视频模型。")
        else:
            print(f"   [ERR] 参数设置失败: {response.text}")
    except Exception as e:
        print(f"   [ERR] 请求异常: {e}")


def upload_frames():
    print(f"\n1. 开始为用户 {USER_ID} 上传图片流...")

    if not os.path.exists(FRAME_DIR):
        print(f"   [ERR] 文件夹不存在: {FRAME_DIR}")
        return

    # 获取所有图片并排序
    files = [f for f in os.listdir(FRAME_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    files.sort()

    # 限制上传数量用于测试 (比如前 15 帧)
    files_to_upload = files[:15]

    if not files_to_upload:
        print("   [WARN] 没有找到图片文件")
        return

    for filename in files_to_upload:
        file_path = os.path.join(FRAME_DIR, filename)

        # 确保文件关闭后再进行下一次循环
        with open(file_path, 'rb') as f:
            # 注意：files 参数的 key 必须是 'file'
            files_dict = {'file': (filename, f, 'image/jpeg')}
            data_dict = {'user_id': USER_ID, 'format': 'jpg'}

            try:
                # 这里的 timeout 设置为 10 秒，防止卡死
                response = requests.post(f"{API_URL}/upload_video_data", files=files_dict, data=data_dict, timeout=10)
                if response.status_code == 200:
                    print(f"   [OK] {filename} 上传成功")
                else:
                    print(f"   [ERR] {filename} 上传失败: {response.text}")
            except Exception as e:
                print(f"   [ERR] 请求异常: {e}")


def trigger_predict():
    print(f"\n2. 请求预测结果...")
    payload = {
        "task_id": "task_automation",
        "user_ids": [USER_ID],
        "user_id": USER_ID  # 之前修正的必填项
    }

    try:
        response = requests.post(f"{API_URL}/predict_by_userIds", json=payload)
        if response.status_code == 200:
            result = response.json()
            # 打印结果
            print(f"\n>>> 预测成功!")
            print(f"Response: {result}")
        else:
            print(f"   [ERR] 预测失败: {response.text}")
    except Exception as e:
        print(f"   [ERR] 请求异常: {e}")


if __name__ == "__main__":
    # 1. 先配置系统 (这一步至关重要，它告诉后端忽略心率数据)
    set_system_params()

    # 2. 上传数据
    upload_frames()

    # 3. 触发预测
    trigger_predict()