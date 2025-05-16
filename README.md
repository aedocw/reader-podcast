WORK IN PROGESS

This script aims to create a podcast feed of articles sent to it.

```
python -m venv .venc
source .venv/bin/activate
pip install -r requirements.txt
python serve.py
```

Then visit http://127.0.0.1:8025/add and add a URL

Add http://127.0.0.1:8025/feed.xml to your podcast app to follow your podcast

These instructions are not right! Need to make a .env file, specify URL and port there...

TODO:
LOTS of stuff!
* Individual user account
* Authentication
* Nicer web form
* Probably tons of room for optimization
* LOTS of room for error handling, right now it does none
* Dockerize for ease of installation, presumably behind Caddy

For now:
* Put URL and any other params into .env file
* Require key in URL
* Put in docker compose

Build docker image with `docker image build -t reader-podcast .`

docker-compose.yml
  reader-podcast:
    hostname: <hostname>
    container_name: reader-podcast
    image: reader-podcast:latest
    env_file:
      - "reader-podcast.env"
    ports:
      - "8025:8025"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
    volumes:
      - reader-podcast-mp3:/usr/src/app/mp3

Example reader-podcast.env file:
```
KEY="somesecretkeyhere"
URL="https://<your URL>"
PORT="8025"
```