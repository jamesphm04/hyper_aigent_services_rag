from app import create_app
from flask import Flask
from app.redis.redis import redis_client

app:Flask = create_app()

if __name__ == '__main__':
    redis_client.flushdb()
    app.run(host='0.0.0.0', port=5003, debug=True)
