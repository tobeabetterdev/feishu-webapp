FROM python:3.11-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ARG PIP_FALLBACK_INDEX_URL=https://pypi.org/simple
ARG PIP_FALLBACK_TRUSTED_HOST=pypi.org

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && (pip install --no-cache-dir \
        -i ${PIP_INDEX_URL} \
        --trusted-host ${PIP_TRUSTED_HOST} \
        -r requirements.txt \
        || pip install --no-cache-dir \
        -i ${PIP_FALLBACK_INDEX_URL} \
        --trusted-host ${PIP_FALLBACK_TRUSTED_HOST} \
        -r requirements.txt)

# 复制源代码
COPY . .

# 创建输出目录
RUN mkdir -p outputs

# 暴露端口
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
