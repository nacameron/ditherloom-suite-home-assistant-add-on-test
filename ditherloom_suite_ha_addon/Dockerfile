FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache python3 py3-pip font-dejavu

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --break-system-packages --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY renderer /app/renderer

ENV DITHERLOOM_DATA_DIR=/data/ditherloom
EXPOSE 8099
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099"]

