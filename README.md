<h3 align="center">pdf-document-layout-analysis-async</h3>



## Dependencies
* Docker Desktop 4.25.0 [install link](https://www.docker.com/products/docker-desktop/)


## Docker containers
A redis server is needed to use the service asynchronously. For that matter, it can be used the 
command `make start:testing` that has a built-in 
redis server.

Containers with `make start`

![Alt logo](readme_pictures/docker_compose_up.png?raw=true "docker-compose up")

Containers with `make start:testing`

![Alt logo](readme_pictures/docker_compose_redis.png?raw=true "docker-compose -f docker-compose-service-with-redis.yml up")


## How to use it asynchronously
1. Send PDF to extract

    curl -X POST -F 'file=@/PATH/TO/PDF/pdf_name.pdf' localhost:5051/async_extraction/[tenant_name]

![Alt logo](readme_pictures/send_materials.png?raw=true "Send PDF to extract")


2. Add extraction task

To add an extraction task, a message should be sent to a queue.

Python code:

    queue = RedisSMQ(host=[redis host], port=[redis port], qname='segmentation_tasks', quiet=True)
    message_json = '{"tenant": "tenant_name", "task": "segmentation", "params": {"filename": "pdf_file_name.pdf"}}'
    message = queue.sendMessage(message_json).exceptions(False).execute()


![Alt logo](readme_pictures/extraction.png?raw=true "Add extraction task")

3. Get paragraphs

When the segmentation task is done, a message is placed in the results queue:

    queue = RedisSMQ(host=[redis host], port=[redis port], qname='segmentation_results', quiet=True)
    results_message = queue.receiveMessage().exceptions(False).execute()

    # The message.message contains the following information:
    # {"tenant": "tenant_name", 
    # "task": "pdf_name.pdf", 
    # "success": true, 
    # "error_message": "", 
    # "data_url": "http://localhost:5051/get_paragraphs/[tenant_name]/[pdf_name]"
    # "file_url": "http://localhost:5051/get_xml/[tenant_name]/[pdf_name]"
    # }


    curl -X GET http://localhost:5051/get_paragraphs/[tenant_name]/[pdf_name]
    curl -X GET http://localhost:5051/get_xml/[tenant_name]/[pdf_name]

or in python

    requests.get(results_message.data_url)
    requests.get(results_message.file_url)

![Alt logo](readme_pictures/get_paragraphs.png?raw=true "Get paragraphs")


## HTTP server
![Alt logo](readme_pictures/http_server.png?raw=true "HTTP server")

The container `HTTP server` is coded using Python 3.9 and uses the [FastApi](https://fastapi.tiangolo.com/) web framework.

If the service is running, the end point definitions can be founded in the following url:

    http://localhost:5051/docs

The end points code can be founded inside the file `app.py`.

The errors are reported to the file `docker_volume/service.log`, if the configuration is not changed (see [Get service logs](#get-service-logs))


## Queue processor
![Alt logo](readme_pictures/queue_processor.png?raw=true "Queue processor")

The container `Queue processor` is coded using Python 3.9, and it is on charge of the communication with redis. 

The code can be founded in the file `QueueProcessor.py` and it uses the library `RedisSMQ` to interact with the 
redis queues.


## Service configuration
Some parameters could be configured using environment variables. If a configuration is not provided,
the defaults values are used.

Default parameters:

    REDIS_HOST=redis_paragraphs
    REDIS_PORT=6379
    MONGO_HOST=mongo_paragraphs
    MONGO_PORT=28017
    SERVICE_HOST=http://127.0.0.1
    SERVICE_PORT=5051


## Set up environment for development
It works with Python 3.12 [install] (https://runnable.com/docker/getting-started/)

    make install_venv

## Execute tests

    make test

