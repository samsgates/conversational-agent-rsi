FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY apps apps
COPY services services
COPY packages packages
RUN pip install --no-cache-dir .
CMD ["python","-m","services.worker_runtime.main"]
