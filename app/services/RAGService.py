import os 
from langchain_openai import ChatOpenAI
from app.services.FileService import FileService
from app.services.SQLService import SQLService
from logging import Logger

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")

class RAGService:
    def __init__(self, logger: Logger):
        self.logger = logger
        
        self.model = ChatOpenAI(
            model_name=OPENAI_MODEL_NAME,
            api_key=OPENAI_API_KEY
        )

    def run(self, messages):
        pass