from app.dtos.chat_dtos import AskRequestDTO, AskResponseDTO, AnswerDTO
from flask import Blueprint, request, jsonify, current_app
from app.services.RAGService import RAGService

chat_blueprint = Blueprint('chat_blueprint', __name__)

@chat_blueprint.route('/ask', methods=['POST'])
def ask():
    logger = current_app.logger
    rag_service: RAGService = current_app.rag_service
    try:
        data = request.get_json()
        request_dto = AskRequestDTO(**data)
        logger.info(f"Received ask request: {request_dto}")

        answer = rag_service.run_chain(
            file_id=request_dto.fileID,
            question=request_dto.question
        )
        
        answer_dto = AnswerDTO(
            answer=answer,
            location=["file_location_placeholder"]  
        )
        
        response_dto = AskResponseDTO(
            status="success",
            message="Ask request received successfully",
            data=[answer_dto]
        )
        
        return jsonify(response_dto.__dict__), 200
    except Exception as e:
        logger.error(f"Error processing ask request: {e}")
        return jsonify({"error": "Invalid request format"}), 400