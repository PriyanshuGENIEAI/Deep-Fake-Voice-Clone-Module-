FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for audio processing (ffmpeg for codecs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python deps
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Optionally override torch install source at build time
#   docker build --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu -t chatterbox .
ARG TORCH_INDEX_URL=
RUN if [ -n "$TORCH_INDEX_URL" ]; then \
      pip install --no-cache-dir --index-url $TORCH_INDEX_URL torch torchaudio ; \
    fi

# Copy source and install package
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8000
ENV CHATTERBOX_API_HOST=0.0.0.0 \
    CHATTERBOX_API_PORT=8000

CMD ["chatterbox-api"]
