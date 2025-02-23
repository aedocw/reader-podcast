WORK IN PROGESS

This script aims to create a podcast feed of articles sent to it.

```
python -m venv .venc
source .venv/bin/activate
pip install -r requirements.txt
python serve.py
```

Then visit http://127.0.0.1:5000/add and add a URL

Add http://127.0.0.1:5000/feed.xml to your podcast app to follow your podcast

TODO:
LOTS of stuff!
* Individual user account
* Authentication
* Nicer web form
* Probably tons of room for optimization
* LOTS of room for error handling, right now it does none
* Dockerize for ease of installation, presumably behind Caddy