from app.dtos.chat_dtos import AskRequestDTO, AskResponseDTO, AnswerDTO
from flask import Blueprint, request, jsonify, current_app
from app.redis.redis import redis_client
from app.services.RAGService import RAGService
from app.services.SQLService import SQLService
from app.celery.tasks import process_file_task


chat_blueprint = Blueprint('chat_blueprint', __name__)

@chat_blueprint.route('/ask', methods=['POST'])
def ask():
    logger = current_app.logger
    rag_service: RAGService = current_app.rag_service
    try:
        data = request.get_json()
        request_dto = AskRequestDTO(**data)
        logger.info(f"Received ask request: {request_dto}")
        
        #Check for being processed file
        # Check if the file is already being processed
        redis_key = f"processing:{request_dto.fileID}"
        
        if redis_client.get(redis_key):
            logger.info(f"File {request_dto.fileID} is already being processed.")
            
            answer_dto = AnswerDTO(
                answer="File is being processed, please try again later in a few minutes.",
                location=["file_location_placeholder"]  
            )
            
            response_dto = AskResponseDTO(
                status="processing",
                message="File is being processed, please try again later.",
                data=[answer_dto]
            )
            
            return jsonify(response_dto.__dict__), 200
        
        # Check if the file exists in the database
        file_exists = rag_service.file_exists(request_dto.fileID)
        if not file_exists:
            logger.error(f"File with ID {request_dto.fileID} does not exist. Processing the file now, please try again later in a few minutes.")
            
            redis_client.set(redis_key, 'processing', ex=600)  # Set a 10m expiration for the processing key
            task = process_file_task.apply_async(args=[request_dto.fileID])
            
            answer_dto = AnswerDTO(
                answer="File does not exist, please try again later in a few minutes.",
                location=["file_location_placeholder"]  
            )
            
            response_dto = AskResponseDTO(
                status="error",
                message="File does not exist, please try again later.",
                task_id=task.id,
                data=[answer_dto]
            )
            
            return jsonify(response_dto.__dict__), 200        

        answer = rag_service.run_chain(
            file_id=request_dto.fileID,
            question=request_dto.question
        )
        
        answer_dto = AnswerDTO(
            answer=answer,
            location=["file_location_placeholder"]  
        )
        
        logger.info(f"Answer generated: {answer_dto}")
        
        response_dto = AskResponseDTO(
            status="success",
            message="Ask request received successfully",
            data=[answer_dto]
        )
        
        return jsonify(response_dto.__dict__), 200
    except Exception as e:
        logger.error(f"Error processing ask request: {e}")
        return jsonify({"error": "Invalid request format"}), 400