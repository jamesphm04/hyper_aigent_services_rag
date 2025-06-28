from flask import Blueprint, request, jsonify
from app.services.RAGService import RAGService
from app.services.SQLService import SQLService
from app.dtos.chat_dtos import AskRequestDTO, AskResponseDTO
from logging import Logger


def create_chat_blueprint(logger: Logger, sql_service: SQLService, rag_service: RAGService) -> Blueprint:
    chat_blueprint = Blueprint('chats', __name__, url_prefix='/services/rag/chats')
    
    
    @chat_blueprint.route('/ask', methods=['POST'])   
    def ask():
        try:
            data = request.get_json()
            request_dto = AskRequestDTO(**data)
            logger.info(f"Received ask request: {request_dto}")

            # Here you would process the request with rag_service and/or sql_service
            # For demonstration, let's assume an empty list of answers
            response_dto = AskResponseDTO(
                status="success",
                message="Ask request received successfully",
                data=[]
            )
            return jsonify(response_dto.__dict__), 200
        except Exception as e:
            return jsonify({"error": "Invalid request format"}), 400