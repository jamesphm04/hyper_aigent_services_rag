import os 
from src.services.SQLService import SQLService
from logging import Logger
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain.schema.document import Document
import uuid
from langchain_core.runnables import Runnable
from typing import List
import json
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage
from collections import defaultdict

from config import OPENAI_API_KEY, ANTHROPIC_API_KEY, PG_VECTOR_CONNECTION_STRING, PG_VECTOR_CONNECTION_STRING_DOCKER, TOP_K
def parse_docs(retriever_results: dict) -> dict:
    images = []
    texts = []
    
    retrieved_docs = retriever_results["result"]
    for page_number, docs in retrieved_docs.items():
        
        for doc in docs:
            if doc.metadata.get("type") == "Image":
                images.append(doc.page_content)
            else:
                type_and_text = f"{doc.metadata.get('type')}: {doc.page_content}"
                texts.append(type_and_text)
    return {"images": images, "texts": texts}

def build_prompt(kwargs):
    docs_by_type = kwargs["context"]
    user_question = kwargs["question"]

    context_text = ""
    if len(docs_by_type["texts"]) > 0:
        for text_element in docs_by_type["texts"]:
            context_text += text_element.strip() + "\n"

    # construct prompt with context (including images)
    prompt_template = f"""You are a document analysis assistant. Answer questions using ONLY the provided context. Follow these strict guidelines:

    RESPONSE REQUIREMENTS:
    - ONLY use information explicitly stated in the context
    - DO NOT add external knowledge, assumptions, or inferences
    - If information is not in the context, clearly state "Information not available in provided context"
    - Be concise, logical, and professional
    - Structure responses clearly with proper organization

    CONTEXT ELEMENT TYPES:
    - Formula: Mathematical formulas and equations
    - FigureCaption: Text describing figures, charts, or images
    - NarrativeText: Complete sentences forming coherent paragraphs
    - ListItem: Individual items within lists
    - Title: Document titles and headings
    - Address: Physical addresses
    - EmailAddress: Email contact information
    - Image: Image metadata and descriptions
    - PageBreak: Page separation indicators
    - Table: Structured tabular data
    - Header: Document headers
    - Footer: Document footers
    - CodeSnippet: Programming code or technical snippets
    - PageNumber: Page numbering
    - UncategorizedText: Other textual content

    RESPONSE FORMAT:
    1. Answer: State the answer clearly and concisely
    2. Supporting Evidence: Quote relevant context sections
    3. Limitations: Note if information is incomplete or unavailable

    PROHIBITED ACTIONS:
    - Do not speculate or make assumptions
    - Do not use knowledge beyond the provided context
    - Do not provide partial answers as complete information
    - Do not rephrase context as new insights

    CONTEXT:
    {context_text}

    QUESTION:
    {user_question}

    RESPONSE:"""

    prompt_content = [{"type": "text", "text": prompt_template}]

    if len(docs_by_type["images"]) > 0:
        for image in docs_by_type["images"]:
            
            prompt_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                }
            )

    return ChatPromptTemplate.from_messages(
        [
            HumanMessage(content=prompt_content),
        ]
    )
class CustomRetriever(Runnable):
    def __init__(self, file_id, embeddings: OpenAIEmbeddings, sql_service: SQLService, vector_store: PGVector, threshold=0.5, id_key="chunk_id"):
        self.file_id = file_id
        self.embeddings = embeddings
        self.sql_service = sql_service
        self.vector_store = vector_store
        self.threshold = threshold
        self.id_key = id_key

    def invoke(self, input: str, config: dict = None) -> List[Document]:
        # Step 1: Search vector DB
        retrieved = self.vector_store.similarity_search_with_score(input, k=TOP_K)
        filtered = [doc for doc, score in retrieved if score >= self.threshold]
        chunk_ids = [doc.metadata[self.id_key] for doc in filtered]

        # Step 2: Get full original content
        result = defaultdict(list)  # page_number -> List[Document]
        
        for chunk_id in chunk_ids:
            db_result = self.sql_service.execute_query(
                f"SELECT * FROM public.rag_original_chunks WHERE chunk_id = %s",
                (chunk_id,),
                fetchone=True
            )
            
            if not db_result:
                continue
            
            
            content = db_result[4]
            chunk_type = db_result[3]
            
            if chunk_type == "image":
                elm = json.loads(content)
                
                metadata = elm["metadata"]
                
                page_content = metadata.get("image_base64", "")
                coordinates = metadata.get("coordinates", {})
                page_number = metadata.get("page_number", 0)
                
                doc = Document(
                    page_content=page_content,
                    metadata={
                        "type": "Image",
                        "coordinates": coordinates,
                        "page_number": page_number
                    }
                )
                result[page_number].append(doc)
            else:
                elememnts = json.loads(content)
                for elm in elememnts:
                    metadata = elm["metadata"]
                    
                    type = elm["type"]
                    page_content = elm.get("text", "")
                    coordinates = metadata.get("coordinates", {})
                    page_number = metadata.get("page_number", 0)
                    
                    if type == "Image":
                        page_content = metadata.get("image_base64", "")
                    
                    doc = Document(
                        page_content=page_content,
                        metadata={
                            "type": type,
                            "coordinates": coordinates,
                            "page_number": page_number
                        }
                    )
                    result[page_number].append(doc)
        return {"result": dict(result), "file_id": self.file_id}
class RAGService:
    def __init__(self, logger: Logger, sql_service: SQLService, is_docker_build: bool = False):
        self.is_docker_build = is_docker_build
        self.logger = logger
        self.sql_service = sql_service
        
        self.model = ChatAnthropic(temperature=0.5, model="claude-3-5-haiku-20241022", api_key=ANTHROPIC_API_KEY)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
        
        self.id_key = "chunk_id"
        
    def file_exists(self, file_id: int) -> bool:
        self.logger.info(f"Checking if file with ID {file_id} exists in the database.")
        exists = self.sql_service.execute_query(
            "SELECT EXISTS(SELECT 1 FROM public.rag_original_chunks WHERE document_id = %s)",
            (file_id,),
            fetchone=True
        )
        return exists[0] if exists else False
        
        
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
        
        images_base64 = [image.metadata.image_base64 for image in images]
        
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self.model | StrOutputParser()
        image_summaries = chain.batch(images_base64, {"max_concurrency": 5})
        
        return image_summaries

    def summarize_and_save_to_vector_db(self, file_id, tables, texts, images):
        
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
        
        connection_string = PG_VECTOR_CONNECTION_STRING_DOCKER if self.is_docker_build else PG_VECTOR_CONNECTION_STRING
        
        vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=str(file_id),  # Use file_id as collection name
            connection=connection_string,
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

    def get_retriever(self, file_id: str, threshold=0.3):
        
        connection_string = PG_VECTOR_CONNECTION_STRING_DOCKER if self.is_docker_build else PG_VECTOR_CONNECTION_STRING
        
        vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=str(file_id),
            connection=connection_string,
        )
        
        return CustomRetriever(
            file_id=file_id,
            embeddings=self.embeddings,
            sql_service=self.sql_service,
            vector_store=vector_store,
            threshold=threshold,
            id_key=self.id_key
        )
    
    def get_chain(self, file_id: str) -> Runnable:
        retriever = self.get_retriever(file_id)
        
        return (
            {
                "context": retriever | RunnableLambda(parse_docs),
                "question": RunnablePassthrough(),
            }
            | RunnableLambda(build_prompt)
            | self.model
            | StrOutputParser()
        )
        
    def run_chain(self, file_id, question: str) -> str:
        chain = self.get_chain(str(file_id))
        response = chain.invoke(question)
        return response