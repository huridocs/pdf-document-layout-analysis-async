from sys import maxsize

from redis import exceptions
from rsmq import RedisSMQ

from configuration import QUEUES_NAMES

REDIS_HOST = "127.0.0.1"
REDIS_PORT = "6379"


def delete_queues():
    try:
        for queue_name in QUEUES_NAMES.split():
            for suffix in ["_tasks", "_results"]:
                queue = RedisSMQ(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    qname=queue_name + suffix,
                    quiet=False,
                )

                queue.deleteQueue().exceptions(False).execute()
                queue.createQueue(maxsize=-1, vt=120).exceptions(False).execute()

        print("Queues properly deleted")

    except exceptions.ConnectionError:
        print("No redis connection")


if __name__ == "__main__":
    delete_queues()
