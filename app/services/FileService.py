import subprocess
import tempfile
import os
from logging import Logger
from app.services.SQLService import SQLService
from app.services.RAGService import RAGService
from unstructured.partition.pdf import partition_pdf
import base64
from IPython.display import Image, display
import json

class FileService:
    def __init__(self, logger: Logger, sql_service: SQLService, rag_service: RAGService):
        self.logger = logger
        self.sql_service = sql_service
        self.rag_service = rag_service
        
    def doc_to_pdf(self, file_bytes: bytes) -> bytes:
        try:
            # 1. Save file_bytes to a temp .docx file
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as input_file:
                input_file.write(file_bytes)
                
                
                self.logger.info(f"Temporary DOCX file created at: {input_file.name}")
                
                input_path = input_file.name

            # 2. Define output path
            output_dir = tempfile.gettempdir()

            # 3. Convert using LibreOffice
            subprocess.run([
                "libreoffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, input_path
            ], check=True)

            output_path = os.path.join(
                output_dir, os.path.splitext(os.path.basename(input_path))[0] + ".pdf"
            )

            # 4. Read converted PDF
            with open(output_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()

            # 5. Clean up
            os.remove(input_path)
            os.remove(output_path)

            return pdf_bytes

        except Exception as e:
            self.logger.error(f"Failed to convert DOCX to PDF: {e}")
            raise
        
    def get_images_base64(self, chunks: list) -> list[str]:
        images_b64 = []
        for chunk in chunks:
            if "CompositeElement" in str(type(chunk)):
                chunk_els = chunk.metadata.orig_elements
                for el in chunk_els:
                    if "Image" in str(type(el)):
                        images_b64.append(el.metadata.image_base64)
        return images_b64
    
    def get_tables_and_texts(self, chunks: list) -> tuple[list, list]:
        # separate tables from texts
        tables = []
        texts = []

        for chunk in chunks:
            if "Table" in str(type(chunk)):
                tables.append(chunk)

            if "CompositeElement" in str(type((chunk))):
                texts.append(chunk)
        return tables, texts
    
    def get_chunks(self, file_path: str) -> list:
        self.logger.info(f"Chunking file: {file_path}...")
        chunks = partition_pdf(
            filename=file_path,
            infer_table_structure=True,  # extract tables
            strategy="hi_res",  # use high resolution for better quality
            extract_image_block_types=["Image"],  # extract table as image
            extract_image_block_to_payload=True,  # extract image as payload in base64
            chunking_strategy="by_title",  # or 'basic'
            max_characters=10000,  # defaults to 500
            combine_text_under_n_chars=2000,  # defaults to 0
            new_after_n_chars=6000,
        )
        return chunks
    
    def display_base64_image(self, base64_code):
        # Decode the base64 string to binary
        image_data = base64.b64decode(base64_code)
        # Display the image
        display(Image(data=image_data))
    
    def prepare_data_for_rag(self, file_id: int) -> bool:
        try:
            # Download the file from the database
            file_path, file_name = self.sql_service.download_file_by_id(file_id)
            self.logger.info(f"File downloaded: {file_path}, Name: {file_name}")
            
            chunks = self.get_chunks(file_path)
            
            tables, texts = self.get_tables_and_texts(chunks)
            images = self.get_images_base64(chunks)
            
            self.logger.info(f"Tables found: {len(tables)}, Texts found: {len(texts)}, Images found: {len(images)}")
            
            # Summarize and save to vector database
            self.logger.info("Saving data to vector database...")
            result = self.rag_service.summarize_and_save_to_vector_db(tables, texts, images)
            
            if not result:
                self.logger.error("Failed to summarize and save data to vector database.")
                return False
            
            # Save original chunks to the database
            # Save tables
            if tables:
                self.logger.info(f"Saving {len(tables)} tables to the database.")
                self.sql_service.save_original_tables(file_id, tables, result['table_ids'])
            # Save texts
            if texts:
                self.logger.info(f"Saving {len(texts)} texts to the database.")
                self.sql_service.save_original_texts(file_id, texts, result['text_ids'])
            # Save images
            if images:
                self.logger.info(f"Saving {len(images)} images to the database.")
                self.sql_service.save_original_images(file_id, images, result['image_ids'])
            return True
        except Exception as e:
            self.logger.error(f"Error preparing data for RAG: {e}")
            return False
