import logging
import os
from contextlib import asynccontextmanager

import pymongo
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import PlainTextResponse
import sys

from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
import sentry_sdk

# from data.Paragraphs import Paragraphs
# from data.SegmentBox import SegmentBox
# from extract_pdf_paragraphs.extract_paragraphs import get_paths, extract_paragraphs
# from extract_pdf_paragraphs.pdf_to_xml import pdf_content_to_pdf_path
# from data.ExtractionData import ExtractionData
# from pdf_file.PdfFile import PdfFile
import configuration

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.mongodb_client = pymongo.MongoClient(f"{configuration.MONGO_HOST}:{configuration.MONGO_PORT}")
    yield
    app.mongodb_client.close()


app = FastAPI(lifespan=lifespan)

logger.info("Get PDF paragraphs service has started")

try:
    sentry_sdk.init(
        os.environ.get("SENTRY_DSN"),
        traces_sample_rate=0.1,
        environment=os.environ.get("ENVIRONMENT", "development"),
    )
    app.add_middleware(SentryAsgiMiddleware)
except Exception:
    pass


@app.get("/")
async def info():
    logger.info("Get PDF paragraphs info endpoint")
    return sys.version


@app.get("/error")
async def error():
    logger.error("This is a test error from the error endpoint")
    raise HTTPException(status_code=500, detail="This is a test error from the error endpoint")

#
# @app.post("/")
# async def post_extract_paragraphs(file: UploadFile):
#     filename = '"No file name! Probably an error about the file in the request"'
#     try:
#         filename = file.filename
#         pdf_path = pdf_content_to_pdf_path(file.file.read())
#         pdf_segmentation = extract_paragraphs(pdf_path)
#         return Paragraphs(
#             page_width=pdf_segmentation.pdf_features.pages[0].page_width,
#             page_height=pdf_segmentation.pdf_features.pages[0].page_height,
#             paragraphs=[SegmentBox.from_pdf_segment(pdf_segment).dict() for pdf_segment in pdf_segmentation.pdf_segments],
#         )
#     except Exception:
#         logger.error(f"Error segmenting {filename}", exc_info=1)
#         raise HTTPException(status_code=422, detail=f"Error segmenting {filename}")
#
#
# @app.post("/async_extraction/{tenant}")
# async def async_extraction(tenant, file: UploadFile = File(...)):
#     filename = '"No file name! Probably an error about the file in the request"'
#     try:
#         filename = file.filename
#         pdf_file = PdfFile(tenant)
#         pdf_file.save(pdf_file_name=filename, file=file.file.read())
#         return "task registered"
#     except Exception:
#         logger.error(f"Error adding task {filename}", exc_info=1)
#         raise HTTPException(status_code=422, detail=f"Error adding task {filename}")
#
#
# @app.get("/get_paragraphs/{tenant}/{pdf_file_name}")
# async def get_paragraphs(tenant: str, pdf_file_name: str):
#     try:
#         suggestions_filter = {"tenant": tenant, "file_name": pdf_file_name}
#         pdf_paragraph_db = app.mongodb_client["pdf_paragraph"]
#         extraction_data_dict = pdf_paragraph_db.paragraphs.find_one(suggestions_filter)
#         pdf_paragraph_db.paragraphs.delete_many(suggestions_filter)
#
#         extraction_data = ExtractionData(**extraction_data_dict)
#         return extraction_data.model_dump_json()
#     except TypeError:
#         raise HTTPException(status_code=404, detail="No paragraphs")
#     except Exception:
#         logger.error("Error", exc_info=1)
#         raise HTTPException(status_code=422, detail="An error has occurred. Check graylog for more info")


# @app.get("/get_xml/{tenant}/{pdf_file_name}", response_class=PlainTextResponse)
# async def get_xml(tenant: str, pdf_file_name: str):
#     try:
#         pdf_file_path, xml_file_path, failed_pdf_path = get_paths(tenant, pdf_file_name)
#
#         with open(xml_file_path, mode="r") as file:
#             content = file.read()
#             os.remove(xml_file_path)
#             return content
#     except FileNotFoundError:
#         raise HTTPException(status_code=404, detail="No xml file")
#     except Exception:
#         logger.error("Error", exc_info=1)
#         raise HTTPException(status_code=422, detail="An error has occurred. Check graylog for more info")