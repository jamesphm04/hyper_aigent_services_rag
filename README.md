celery -A app.celery.celery_worker.celery worker \
 --loglevel=info \
 --concurrency=2 \
 --autoscale=10,2 \
 --logfile=logs/celery.log
