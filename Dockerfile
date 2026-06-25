FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y libimage-exiftool-perl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install flask gunicorn

RUN mkdir -p /app/uploads

COPY app.py .

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app", "--timeout", "120"]
