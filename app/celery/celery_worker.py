from app import create_app
from app.extensions import celery

if __name__ == '__main__':
    celery.start()