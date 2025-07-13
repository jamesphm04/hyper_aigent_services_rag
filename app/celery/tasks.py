from app.redis.redis import redis_client
from app.extensions import celery
from celery.signals import worker_init

# Worker initialization - this runs when each worker process starts
@worker_init.connect
def init_worker(**kwargs):
    """Initialize services when worker starts"""
    from app.services.SQLService import SQLService
    from app.services.RAGService import RAGService
    from app.services.FileService import FileService
    from app.helpers.logger import Logger
    
    logger = Logger().get_logger()
    sql_service = SQLService(logger)
    rag_service = RAGService(logger, sql_service)
    file_service = FileService(logger, sql_service, rag_service)
    
    # Store services in celery configuration for this worker
    celery.conf.update({
        'file_service': file_service,
        'rag_service': rag_service,
        'sql_service': sql_service,
        'logger': logger
    })

@celery.task
def process_file_task(id: int):
    # Get services from celery configuration
    file_service = celery.conf.get('file_service')
    logger = celery.conf.get('logger')
    
    
        # Fallback initialization if services are not available
    if not file_service or not logger:
        print(f"{'*'*50}\nServices not initialized in Celery context.\n{'*'*50}")
        
        from app.services.SQLService import SQLService
        from app.services.RAGService import RAGService
        from app.services.FileService import FileService
        from app.helpers.logger import Logger
        
        logger = Logger().get_logger()
        sql_service = SQLService(logger)
        rag_service = RAGService(logger, sql_service)
        file_service = FileService(logger, sql_service, rag_service)
    
    logger.info(f"Processing file with ID: {id}")
    try:
        # Call the file service to process the file
        result = file_service.prepare_data_for_rag(id)
        
        if result:
            logger.info(f"File with ID {id} processed successfully.")
            return {"status": "success", "file_id": id}
        else:
            logger.error(f"Failed to process file with ID {id}.")
            return {"status": "error", "message": "File processing failed."}
    except Exception as e:
        logger.error(f"Error processing file with ID {id}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        # Clean up Redis key after processing
        redis_key = f"processing:{id}"
        if redis_client.exists(redis_key):
            redis_client.delete(redis_key)
            logger.info(f"Removed Redis key: {redis_key}")
        else:
            logger.info(f"Redis key {redis_key} does not exist.")
    
