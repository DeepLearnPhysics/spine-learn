FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    SPINE_SITE_DIR=/app/site \
    SPINE_LESSON=/app/tutorials/01_reconstruction_basics.md
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt \
    && groupadd --gid 10001 spine \
    && useradd --uid 10001 --gid spine --no-create-home spine
COPY spine_learn/__init__.py spine_learn/tutor.py spine_learn/web.py ./spine_learn/
COPY tutorials/01_reconstruction_basics.md ./tutorials/
COPY deploy/gunicorn.conf.py ./deploy/gunicorn.conf.py
COPY _build/site/_build/html/ ./site/
USER 10001:10001
EXPOSE 8080
CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "spine_learn.web:create_app()"]
