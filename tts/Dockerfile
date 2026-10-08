FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 HF_HOME=/models HF_HUB_DISABLE_XET=1
RUN apt-get update && apt-get install -y --no-install-recommends espeak-ng libsndfile1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
WORKDIR /workspace
ENTRYPOINT ["python", "-m", "spine_learn.narration"]
CMD ["build"]
