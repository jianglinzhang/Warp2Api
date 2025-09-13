# 使用您验证过的 Python 3.13 基础镜像
FROM python:3.13-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户，但暂时不切换过去
# RUN useradd -m -u 10014 user

# 安装 uv (作为 root)
RUN pip install uv

# 设置工作目录
WORKDIR /app

# 克隆 GitHub 仓库
RUN git clone https://github.com/jianglinzhang/Warp2Api.git .

# 将我们的启动器脚本复制到镜像中
# 【重要】确保 launcher.py 和 Dockerfile 在同一目录
# COPY launcher.py /app/

# 【核心修复】以 root 用户身份安装系统依赖
# 这样 uv 就有权限写入 /usr/local/lib/python3.13/site-packages/
RUN uv pip compile pyproject.toml --output-file=requirements.lock && \
    uv pip sync --system requirements.lock

# ---- 依赖安装完成，现在处理权限和切换用户 ----

# 创建非 root 用户可写的缓存和本地目录
RUN mkdir -p /app/.cache /app/.local && \
    chown -R 777 /app

# 设置环境变量
ENV UV_CACHE_DIR=/app/.cache/uv
ENV UV_TOOL_DIR=/app/.local/uv/tools
ENV UV_TOOL_BIN_DIR=/app/.local/uv/bin
ENV PYTHONPATH=/app
ENV WARP_LOG_LEVEL=info
ENV WARP_ACCESS_LOG=false
ENV OPENAI_LOG_LEVEL=info
ENV OPENAI_ACCESS_LOG=false


# 设置用户的 PATH
ENV PATH="/app/.local/bin:${PATH}"

# 暴露端口
EXPOSE 8010

USER 10014

# 以 user 用户身份启动 launcher.py
CMD ["python", "start.py"]
