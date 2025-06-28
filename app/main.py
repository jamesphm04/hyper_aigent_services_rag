from flask import Flask
from app.helpers.logger import Logger
from app.services.SQLService import SQLService
from app.services.RAGService import RAGService
from app.controllers.chat_controller import create_chat_blueprint 
from app.controllers.file_controller import create_file_blueprint 


def create_app():
    app = Flask(__name__)
    
    logger = Logger().get_logger()
    app.logger = logger
    
    # Initialize shared services
    sql_service = SQLService(logger)
    rag_service = RAGService(logger)
    
    # Pass these shared services to the controllers
    app.register_blueprint(create_chat_blueprint(logger, sql_service, rag_service))
    app.register_blueprint(create_file_blueprint(logger, sql_service))
    
    return app
    
    
    