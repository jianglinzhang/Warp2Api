FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
ENV WARP_LOG_LEVEL=info
ENV WARP_ACCESS_LOG=true
ENV OPENAI_LOG_LEVEL=info
ENV OPENAI_ACCESS_LOG=true

# 创建必要的目录并设置权限
RUN mkdir -p /app/.cache && \
    mkdir -p /app/.local && \
    chmod -R 777 /app

# 设置 uv 缓存目录到有权限的位置
ENV UV_CACHE_DIR=/app/.cache/uv
ENV UV_TOOL_DIR=/app/.local/uv/tools
ENV UV_TOOL_BIN_DIR=/app/.local/uv/bin
ENV PYTHONPATH=/app

USER 10014
# 设置用户的 PATH
ENV PATH="/app/.local/bin:${PATH}"
    
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .
# USER 10014
CMD ["uv", "run", "./start.py"]


