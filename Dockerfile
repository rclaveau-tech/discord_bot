FROM python:3.10-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN apk add --no-cache git ffmpeg opus-dev

RUN pip install --no-cache-dir -r requirements.txt

RUN apk del git

COPY bot_merge.py .

CMD [ "python", "bot_merge.py" ]
