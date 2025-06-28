import subprocess
import tempfile
import os
from logging import Logger

class ConvertService:
    def __init__(self, logger: Logger):
        self.logger = logger
        
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