FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" "pydantic>=2.6"
COPY backend backend
COPY frontend frontend
ENV SAHAYAK_DB=/data/sahayak.db
VOLUME /data
WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
