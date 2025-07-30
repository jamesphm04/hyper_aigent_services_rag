from urllib.parse import urlparse
import os 
import psycopg2
from logging import Logger
from src.entities.DocumentEntity import DocumentEntity
import json
from config import DATABASE_URL, DATABASE_URL_DOCKER

class SQLService:
    def __init__(self, logger: Logger, is_docker_build: bool = False):
        self.is_docker_build = is_docker_build
        self.logger = logger
        self.db_config = self._get_db_config()

    def _get_db_config(self):
        url = urlparse(DATABASE_URL_DOCKER if self.is_docker_build else DATABASE_URL)
        return {
            "dbname": url.path[1:],
            "user": url.username,
            "password": url.password,
            "host": url.hostname,
            "port": url.port
        }

    def execute_query(self, query, params=None, commit=False, fetchone=False, fetchall=False):
        try:
            with psycopg2.connect(**self.db_config) as connection:
                with connection.cursor() as cur:
                    cur.execute(query, params)

                    if commit:
                        connection.commit()
                        return True

                    if fetchone:
                        
                        return cur.fetchone()

                    if fetchall:
                        return cur.fetchall()
        except Exception as e:
            self.logger.error(f"An error occurred while executing the query: {e}")
            return None

    def test(self, query, params=None, commit=False, fetchone=False, fetchall=False):
        return self.execute_query(query, params, commit, fetchone, fetchall)

    def convert_to_pdf(self, file_id: int):
        from src.services.FileService import FileService
        file_service = FileService(self.logger)
        try:
            with psycopg2.connect(**self.db_config) as conn:
                conn.autocommit = False
                with conn.cursor() as cur:
                    cur.execute("SELECT content FROM documents WHERE id = %s", (file_id,))
                    row = cur.fetchone()
                    if not row:
                        return None

                    large_object = conn.lobject(row[0], 'rb')
                    file_data = large_object.read()
                    large_object.close()

                    pdf_data = file_service.doc_to_pdf(file_data)

                    pdf_lo = conn.lobject(0, 'wb')
                    pdf_lo.write(pdf_data)
                    pdf_oid = pdf_lo.oid
                    pdf_lo.close()

                    cur.execute("""
                        UPDATE documents 
                        SET content = %s,
                            updated_at = NOW(),
                            type = 'pdf'
                        WHERE id = %s
                    """, (pdf_oid, file_id))
                conn.commit()
                return pdf_oid
        except Exception as e:
            self.logger.error(f"Error converting file with ID {file_id} to PDF: {e}")
            return None

    def download_file_by_id(self, file_id: int):
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT content, name, type FROM documents WHERE id = %s", (file_id,))
                    row = cur.fetchone()
                    if not row:
                        return None

                    large_object = conn.lobject(row[0], 'rb')
                    file_data = large_object.read()
                    large_object.close()

                    name = row[1]
                    type = row[2]
                    path = os.path.join('/tmp', 'downloads', f"{file_id}.{type}")
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, 'wb') as f:
                        f.write(file_data)
                    self.logger.info(f"File with ID {file_id} downloaded to {path}")
                    return path, name
        except Exception as e:
            self.logger.error(f"Error downloading file with ID {file_id} to local storage: {e}")
            return None

    def get_file_by_id(self, file_id: int) -> DocumentEntity:
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM documents WHERE id = %s", (file_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    entity = DocumentEntity(*row)

                    large_object = conn.lobject(entity.content, 'rb')
                    file_data = large_object.read()
                    large_object.close()

                    from src.services.FileService import FileService
                    file_service = FileService(self.logger)
                    file_service.doc_to_pdf(file_data)

                    return entity
        except Exception as e:
            self.logger.error(f"Error retrieving file with ID {file_id}: {e}")
            return None

    def save_original_chunks(self, file_id: int, chunks: list, chunk_ids: list, chunk_type: str):
        for idx, comp_elem in enumerate(chunks):
            try:
                content_json = json.dumps([sub_elem.to_dict() for sub_elem in comp_elem.metadata.orig_elements])
                query = """
                    INSERT INTO public.rag_original_chunks (chunk_id, document_id, type, content)
                    VALUES (%s, %s, %s, %s)
                """
                params = (chunk_ids[idx], file_id, chunk_type, content_json)
                self.execute_query(query, params, commit=True)
            except Exception as e:
                self.logger.error(f"Error saving {chunk_type} chunk {idx} for file ID {file_id}: {e}")
                continue

    def save_original_tables(self, file_id: int, tables: list, table_ids: list):
        self.save_original_chunks(file_id, tables, table_ids, 'table')

    def save_original_texts(self, file_id: int, texts: list, text_ids: list):
        self.save_original_chunks(file_id, texts, text_ids, 'text')

    def save_original_images(self, file_id: int, images: list, image_ids: list):
        for idx, img_elm in enumerate(images):
            try:
                query = """
                    INSERT INTO public.rag_original_chunks (chunk_id, document_id, type, content)
                    VALUES (%s, %s, %s, %s)
                """
                params = (image_ids[idx], file_id, 'image', json.dumps(img_elm.to_dict()))
                self.execute_query(query, params, commit=True)
            except Exception as e:
                self.logger.error(f"Error saving image chunk {idx} for file ID {file_id}: {e}")
                continue
            
    def is_processed(self, file_id: int) -> bool:
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM rag_original_chunks WHERE document_id = %s", (file_id,))
                    row = cur.fetchone()
                    if row and row[0]:
                        return True
            return False
        except Exception as e:
            self.logger.error(f"Error checking if file with ID {file_id} is processed: {e}")
            return False
