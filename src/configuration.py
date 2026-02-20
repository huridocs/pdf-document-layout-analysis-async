import logging
import os
from os.path import join
from pathlib import Path
import graypy

QUEUES_NAMES = os.environ.get("QUEUES_NAMES", "segmentation development_segmentation ocr development_ocr")

SERVICE_HOST = os.environ.get("SERVICE_HOST", "http://127.0.0.1")
SERVICE_PORT = os.environ.get("SERVICE_PORT", "5051")
GRAYLOG_IP = os.environ.get("GRAYLOG_IP")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
MONGO_HOST = os.environ.get("MONGO_HOST", "localhost")
MONGO_PORT = os.environ.get("MONGO_PORT", "25017")
SENTRY_DSN = os.environ.get("SENTRY_DSN")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
USE_FAST = os.environ.get("USE_FAST", "True").lower() in ("true", "1", "t")
USE_LOCAL_SEGMENTATION = os.environ.get("USE_LOCAL_SEGMENTATION", "True").lower() in ("true", "1", "t")


DOCUMENT_LAYOUT_ANALYSIS_PORT = os.environ.get("DOCUMENT_LAYOUT_ANALYSIS_PORT", "5060")
WORKER_PDF_LAYOUT = os.environ.get("WORKER_PDF_LAYOUT", "http://localhost")
DOCUMENT_LAYOUT_ANALYSIS_URL = f"{WORKER_PDF_LAYOUT}:{DOCUMENT_LAYOUT_ANALYSIS_PORT}"

APP_PATH = Path(__file__).parent.absolute()
ROOT_PATH = Path(__file__).parent.parent.absolute()
DATA_PATH = join(ROOT_PATH, "data")

OCR_OUTPUT = Path(DATA_PATH, "ocr_output")

handlers = [logging.StreamHandler()]
if GRAYLOG_IP:
    handlers.append(graypy.GELFUDPHandler(GRAYLOG_IP, 12201, localname="pdf_paragraphs_extraction"))

logging.root.handlers = []
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers)
service_logger = logging.getLogger(__name__)


PROMPTS = {
    "Prompt 3": """Please translate the following text into {language_to_name}. Follow these guidelines:
1. Maintain the original layout and formatting.
2. Translate all text accurately without omitting any part of the content.
3. Preserve the tone and style of the original text.
4. Do not include any additional comments, notes, or explanations in the output; provide only the translated text.
5. Only translate the text between ``` and ```. Do not output any other text or character.

Here is the text to be translated:

```
{text_to_translate}
```
""",
}

LANGUAGES_SHORT = ["en", "fr", "es", "ru", "ar", "sp"]
LANGUAGES = ["English", "French", "Spanish", "Russian", "Arabic", "Spanish"]
