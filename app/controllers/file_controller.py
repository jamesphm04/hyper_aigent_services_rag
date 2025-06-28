from logging import Logger
from app.services.SQLService import SQLService
from flask import Blueprint, request, jsonify


def create_file_blueprint(logger: Logger, sql_service: SQLService) -> Blueprint:
    file_blueprint = Blueprint('files', __name__, url_prefix='/services/rag/files')

    @file_blueprint.route('/convert/<int:id>', methods=['GET'])
    def convert(id: int):
        try:
            logger.info(f"Received convert request for file ID: {id}")
            file = sql_service.convert_to_pdf(id)
            
            if not file:
                logger.error(f"File with ID {id} not found or conversion failed.")
                return jsonify({"error": "File not found or conversion failed"}), 404
            
            
            return jsonify({"message": f"Successfully converted file {id}"}), 200
        except Exception as e:
            logger.error(f"Error retrieving file with ID {id}: {e}")
            return jsonify({"error": "File not found"}), 404
        
        
    return file_blueprint