FROM python:3.9-slim

WORKDIR /usr/src/app

RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

ENV BUCKET_NAME=loayk-bucket-tf

CMD ["python3", "app.py"]