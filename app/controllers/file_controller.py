from flask import Blueprint, jsonify, current_app
from app.celery.tasks import process_file_task

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
    
    try:
        logger.info(f"Received process request for file ID: {id}")
        task = process_file_task.apply_async(args=[id])
        
        return jsonify({
            "message": f"File processing started for file ID {id}",
            "task_id": task.id
        }), 202 # 202 is for accepted requests that are still being processed
        
    except Exception as e:
        logger.error(f"Error processing file with ID {id}: {e}")
        return jsonify({"error": "File processing failed"}), 500