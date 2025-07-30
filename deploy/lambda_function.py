import os

os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

from src.services.SQLService import SQLService
from src.services.RAGService import RAGService
from src.services.FileService import FileService
from src.helpers.logger import Logger

def lambda_handler(event, context):
    id = event.get('id')
    is_docker_build = event.get('is_docker_build', False)
    logger = Logger().get_logger()
    
    logger.info(f"Received event: {event}")
    
    sql_service = SQLService(logger, is_docker_build)
    rag_service = RAGService(logger, sql_service, is_docker_build)
    file_service = FileService(logger, sql_service, rag_service)
    
    #test the connection 
    if int(id) == -1:
        result = sql_service.test("SELECT * FROM users", fetchone=True)
        logger.info(f"Test query result: {result}")
        return {
            "statusCode": 200,
            "message": "Database connection test successful.",
            "result": result
        }
    
    is_processed = sql_service.is_processed(id)
    if is_processed:
        logger.info(f"File with ID {id} has already been processed.")
        return {
            "statusCode": 200,
            "message": f"File {id} has already been processed."
        }
    try:
        logger.info(f"Received process request for file ID: {id}")
        
        result = file_service.prepare_data_for_rag(id)
        if result:
            logger.info(f"File with ID {id} processed successfully.")
            return {
                "statusCode": 200,
                "message": f"Successfully processed file {id}"
            }
        else:
            logger.error(f"Failed to process file with ID {id}.")
            return {
                "statusCode": 500,
                "message": "File processing failed."
            }
    except Exception as e:
        logger.error(f"Error processing file with ID {id}: {e}")
        return {
            "statusCode": 500,
            "message": str(e)
        }
