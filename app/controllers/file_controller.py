from flask import Blueprint, jsonify, current_app
from app.celery.tasks import process_file_task
from app.services.SQLService import SQLService
from app.redis.redis import redis_client

file_blueprint = Blueprint('file_blueprint', __name__)

@file_blueprint.route('/convert/<int:id>', methods=['GET'])
def convert(id: int):
    logger = current_app.logger
    
    try:
        logger.info(f"Received convert request for file ID: {id}")
        file = current_app.sql_service.convert_to_pdf(id)
        
        if not file:
            logger.error(f"File with ID {id} not found or conversion failed.")
            return jsonify({"error": "File not found or conversion failed"}), 404
        
        
        return jsonify({"message": f"Successfully converted file {id}"}), 200
    except Exception as e:
        logger.error(f"Error retrieving file with ID {id}: {e}")
        return jsonify({"error": "File not found"}), 404

@file_blueprint.route('/process/<int:id>', methods=['GET'])
def process(id: int):
    logger = current_app.logger
    sql_service: SQLService = current_app.sql_service
    
    # Check if the file is already being processed
    redis_key = f"processing:{id}"
    
    if redis_client.get(redis_key):
        logger.info(f"File {id} is already being processed.")
        return jsonify({"message": f"File {id} is already being processed"}), 202
    
    # Check if the file has already been processed
    is_processed = sql_service.is_processed(id)
    if is_processed:
        logger.info(f"File with ID {id} has already been processed.")
        return jsonify({"message": f"File {id} has already been processed"}), 200
    
    try:
        logger.info(f"Received process request for file ID: {id}")
        redis_client.set(redis_key, 'processing', ex=600)  # Set a 10m expiration for the processing key
        
        task = process_file_task.apply_async(args=[id])
        
        return jsonify({
            "message": f"File processing started for file ID {id}",
            "task_id": task.id
        }), 202 # 202 is for accepted requests that are still being processed
        
    except Exception as e:
        logger.error(f"Error processing file with ID {id}: {e}")
        return jsonify({"error": "File processing failed"}), 500

@file_blueprint.route('/process/status/<task_id>', methods=['GET'])
def check_for_processing_status(task_id: str):
    logger = current_app.logger
    task = process_file_task.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        return jsonify({"status": "pending"}), 202
    elif task.state == 'SUCCESS':
        return jsonify({"status": "success", "result": task.result}), 200
    elif task.state == 'FAILURE':
        logger.error(f"Task {task_id} failed with error: {task.info}")
        return jsonify({"status": "failure", "error": str(task.info)}), 500
    else:
        return jsonify({"status": task.state}), 200
    
@file_blueprint.route('/<id>', methods=['DELETE'])
def delete_file(id: int):
    
    print(f"Received delete request for file ID: {id}")
    logger = current_app.logger
    sql_service: SQLService = current_app.sql_service
    
    try:
        logger.info(f"Received delete request for file ID: {id}")
        sql_service.delete_by_id(id)
        return jsonify({"message": f"File {id} deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting file with ID {id}: {e}")