from celery import Celery
from app.services.SQLService import SQLService
from app.services.RAGService import RAGService
from app.services.FileService import FileService
from app.helpers.logger import Logger

# Global instances
celery = Celery(
    'hyper_aigent_rag',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

logger = None
sql_service = None
rag_service = None
file_service = None

def init_services():
    global logger, sql_service, rag_service, file_service
    logger = Logger().get_logger()
    sql_service = SQLService(logger)
    rag_service = RAGService(logger, sql_service)
    file_service = FileService(logger, sql_service, rag_service)

    return {
        'logger': logger,
        'sql_service': sql_service,
        'rag_service': rag_service,
        'file_service': file_service,
    }

def init_extensions(app):
    services = init_services()

    app.logger = services['logger']
    app.sql_service = services['sql_service']
    app.rag_service = services['rag_service']
    app.file_service = services['file_service']
    
    # Initialize Celery
    init_celery(app)

def init_celery(app):
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )
    
    # Update task base classes
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    
    # Import tasks to register them
    from app.celery import tasks  
