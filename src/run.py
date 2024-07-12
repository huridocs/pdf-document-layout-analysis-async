from rsmq import RedisSMQ

from data_model.Params import Params
from data_model.Task import Task

if __name__ == '__main__':
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