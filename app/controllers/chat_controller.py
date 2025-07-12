from app.dtos.chat_dtos import AskRequestDTO, AskResponseDTO
from flask import Blueprint, request, jsonify, current_app

chat_blueprint = Blueprint('chat_blueprint', __name__)

@chat_blueprint.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.get_json()
        request_dto = AskRequestDTO(**data)
        current_app.logger.info(f"Received ask request: {request_dto}")

        # Here you would process the request with rag_service and/or sql_service
        # For demonstration, let's assume an empty list of answers
        response_dto = AskResponseDTO(
            status="success",
            message="Ask request received successfully",
            data=[]
        )
        return jsonify(response_dto.__dict__), 200
    except Exception as e:
        current_app.logger.error(f"Error processing ask request: {e}")
        return jsonify({"error": "Invalid request format"}), 400