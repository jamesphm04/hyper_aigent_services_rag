from app.controllers.chat_controller import chat_blueprint
from app.controllers.file_controller import file_blueprint
from flask import Flask

def register_blueprints(app: Flask):
    app.register_blueprint(chat_blueprint, url_prefix='/services/rag/chat')
    app.register_blueprint(file_blueprint, url_prefix='/services/rag/files')
