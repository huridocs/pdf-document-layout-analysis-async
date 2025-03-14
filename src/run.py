from fastapi import UploadFile
from rsmq import RedisSMQ

from PdfFile import PdfFile
from data_model.Params import Params
from data_model.Task import Task
from extract_segments import extract_segments


def extract_segments_from_file(file: UploadFile):
    filename = file.filename
    default_tenant = "default"
    task = Task(tenant=default_tenant, task="extract_segments", params=Params(filename=filename))
    PdfFile(default_tenant).save(pdf_file_name=filename, file=file.file.read())
    extraction_data = extract_segments(task, "default.xml")
    return extraction_data.paragraphs


if __name__ == "__main__":
    extractions_tasks_queue = RedisSMQ(
        host="",
        port="6379",
        qname="segmentation_tasks",
    )
    task = Task(
        tenant="",
        task="",
        params=Params(
            filename="",
        ),
    )

    extractions_tasks_queue.sendMessage(delay=5).message(task.model_dump_json()).execute()
