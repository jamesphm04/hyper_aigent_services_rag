from urllib.parse import urlparse
import os 
import psycopg2
from logging import Logger
from app.entities.DocumentEntity import DocumentEntity
from app.services.ConvertService import ConvertService

class SQLService:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.convert_service = ConvertService(logger)   
        url = urlparse(os.getenv("DATABASE_URL"))
        self.connection = psycopg2.connect(
            dbname=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        self.cursor = self.connection.cursor()

    def close(self):
        """Close the cursor and connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            
    def execute_query(self, query, params=None, commit=False, fetchone=False, fetchall=False):
        try:
            self.cursor.execute(query, params)
            if commit:
                self.connection.commit()
                return True
            if fetchone:
                return self.cursor.fetchone()
            if fetchall:
                return self.cursor.fetchall()
            return None
        except Exception as e:
            self.logger.error(f"An error occurred while executing the query: {e}")
            if commit:
                self.connection.rollback()
            return None
    
    def test(self, query, params=None, commit=False):
        try:
            return self.execute_query(query, params, commit)
        except Exception as e:
            self.logger.error(f"An error occurred while testing the query: {e}")
            return None
        
    def convert_to_pdf(self, file_id: int):
        try:
            row = self.execute_query(
                "SELECT content FROM documents WHERE id = %s", 
                (file_id,), 
                fetchone=True
            )
            if not row:
                return None
            
            # Read the file content from the large object (OID)
            large_object = self.connection.lobject(row[0], 'rb')
            file_data = large_object.read()  # in bytes
            large_object.close()
            
            pdf_data = self.convert_service.doc_to_pdf(file_data)  # Convert the file data to PDF

            # Save the PDF data back to the database as a new large object
            pdf_oid = self.connection.lobject(0, 'wb').oid
            pdf_lo = self.connection.lobject(pdf_oid, 'wb')
            pdf_lo.write(pdf_data)
            pdf_lo.close()

            # Update the document's content to point to the new PDF large object
            self.execute_query(
                """UPDATE documents 
                    SET content = %s,
                        updated_at = NOW(),
                        type = 'pdf'
                    WHERE id = %s
                    """,
                (pdf_oid, file_id),
                commit=True
            )

            return pdf_oid
        except Exception as e:
            self.logger.error(f"Error converting file with ID {file_id} to PDF: {e}")
            self.connection.rollback()
            return None
        
    def download_file_by_id(self, file_id: int):
        try:
            row = self.execute_query(
                "SELECT content, name, type FROM documents WHERE id = %s", 
                (file_id,), 
                fetchone=True
            )
            if not row:
                return None
            
            
            # Read the file content from the large object (OID)
            large_object = self.connection.lobject(row[0], 'rb')
            file_data = large_object.read()  # in bytes
            large_object.close()
            
            # Save the file data to a local file
            name = row[1]
            type = row[2]
            path = os.path.join(os.getcwd(), 'downloads', f"{name}.{type}")
            
            with open(path, 'wb') as f:
                f.write(file_data)
            self.logger.info(f"File with ID {file_id} downloaded to {path}")
            return path
        except Exception as e:
            self.logger.error(f"Error downloading file with ID {file_id} to local storage: {e}")
            return None
        
    def get_file_by_id(self, file_id: int) -> DocumentEntity:
        try:
            row = self.execute_query(
                "SELECT * FROM documents WHERE id = %s", 
                (file_id,), 
                fetchone=True
            )
            if not row:
                return None
            entity = DocumentEntity(*row)
            
            # Read the file content from the large object (OID)
            large_object = self.connection.lobject(entity.content, 'rb')
            file_data = large_object.read() # in bytes
            large_object.close()
            
            self.convert_service.doc_to_pdf(file_data)  # Convert the file data to PDF
            
            return entity
        except Exception as e:
            self.logger.error(f"Error retrieving file with ID {file_id}: {e}")
            return None