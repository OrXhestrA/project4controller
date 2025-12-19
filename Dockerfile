FROM python:3.11-slim

# 【关键修正】更换为清华大学 Debian 镜像源，解决 apt-get 下载失败/超时的问题
# 注意：python:3.11-slim 基于 Debian Trixie/Bookworm，源配置文件通常在 /etc/apt/sources.list.d/debian.sources
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# 设置容器内的工作目录
WORKDIR /app/project4controller

# 复制依赖文件
COPY project4controller/requirements.txt .

# 优化安装环境
RUN pip install setuptools wheel

# 安装所有项目依赖
# 注意：这里不需要再 pip uninstall opencv 了，因为我们要用的就是标准版
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --timeout 600

# 复制源代码
COPY project4controller/ /app/project4controller/

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "run.py"]