FROM python:3.13.7-alpine

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "while true; do python printables-to-rss.py; echo done; sleep 14400; done"]
