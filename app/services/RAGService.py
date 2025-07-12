import os 
from langchain_openai import ChatOpenAI
from app.services.SQLService import SQLService
from logging import Logger
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.pgvector import PGVector
from langchain.schema.document import Document
import uuid

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
PG_VECTOR_CONNECTION_STRING = os.getenv("PG_VECTOR_CONNECTION_STRING")
class RAGService:
    def __init__(self, logger: Logger, sql_service: SQLService):
        self.logger = logger
        self.sql_service = sql_service
        
        self.model = ChatAnthropic(temperature=0.5, model="claude-3-5-haiku-20241022", api_key=ANTHROPIC_API_KEY)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
        
        self.collection_name = "my_docs"
        self.id_key = "chunk_id"
        
        
    def sumarize_tables_and_texts(self, tables, texts):
        self.logger.info("Summarizing tables and texts...")
        
        prompt_text = """
            You are an assistant tasked with summarizing tables and text.
            Give a concise summary of the table or text.

            Respond only with the summary, no additionnal comment.
            Do not start your message by saying "Here is a summary" or anything like that.
            Just give the summary as it is.

            Table or text chunk: {element}

        """
        
        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = {"element": lambda x: x} | prompt | self.model | StrOutputParser()
        
        #Tables
        tables_html = [table.metadata.text_as_html for table in tables]
        table_summaries = chain.batch(tables_html, {"max_concurrency": 5})
        
        #Texts
        text_summaries = chain.batch(texts, {"max_concurrency": 5})
        
        return table_summaries, text_summaries
    
    def summarize_images(self, images):
        self.logger.info("Summarizing images...")
        
        prompt_text = """
            Describe the image in detail. For context,
            the image is part of a research paper explaining the transformers
            architecture. Be specific about graphs, such as bar plots.
        """
        messages = [
            (
                "user",
                [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,{image}"},
                    },
                ],
            )
        ]
        
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self.model | StrOutputParser()
        image_summaries = chain.batch(images, {"max_concurrency": 5})
        
        return image_summaries

    def summarize_and_save_to_vector_db(self, tables, texts, images):
        
        table_summaries, text_summaries = self.sumarize_tables_and_texts(tables, texts)
        image_summaries = self.summarize_images(images)
        
        # Prepare documents for vector store
        
        # Texts
        text_ids = [str(uuid.uuid4()) for _ in texts]
        text_summary_docs = [
            Document(page_content=summary, metadata={self.id_key: text_ids[i]}) for i, summary in enumerate(text_summaries)
        ]
        
        # Tables
        table_ids = [str(uuid.uuid4()) for _ in tables]
        table_summary_docs = [
            Document(page_content=summary, metadata={self.id_key: table_ids[i]}) for i, summary in enumerate(table_summaries)
        ]
        
        # Images
        image_ids = [str(uuid.uuid4()) for _ in images]
        image_summary_docs = [
            Document(page_content=summary, metadata={self.id_key: image_ids[i]}) for i, summary in enumerate(image_summaries)
        ]
        
        # save to vector store
        self.logger.info("Saving documents to vector store...")
        
        vector_store = PGVector(
            embedding_function=self.embeddings,
            collection_name=self.collection_name,
            connection_string=PG_VECTOR_CONNECTION_STRING,
        )
        
        if text_summary_docs:
            vector_store.add_documents(text_summary_docs)
        if table_summary_docs:
            vector_store.add_documents(table_summary_docs)
        if image_summary_docs:
            vector_store.add_documents(image_summary_docs)
        self.logger.info("Documents saved to vector store.")
        
        return {
            "text_ids": text_ids,
            "table_ids": table_ids,
            "image_ids": image_ids
        }

        