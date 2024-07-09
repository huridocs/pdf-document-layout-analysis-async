install:
	. .venv/bin/activate; pip install -r requirements.txt

install_venv:
	python3 -m venv .venv
	. .venv/bin/activate; python -m pip install --upgrade pip
	. .venv/bin/activate; python -m pip install -r dev-requirements.txt

formatter:
	. .venv/bin/activate; command black --line-length 125 .

check_format:
	. .venv/bin/activate; command black --line-length 125 . --check

test:
	. .venv/bin/activate; command cd src; python -m pytest

start:
	docker compose up --build

stop:
	docker compose stop ; docker compose stop -f docker-compose-test.yml

start-test:
	docker compose  -f docker-compose-test.yml up --attach api-pdf-layout --attach queue-processor-pdf-layout --attach worker-pdf-layout --build

start_detached:
	docker compose  -f docker-compose-test.yml up --build -d

upgrade:
	. .venv/bin/activate; pip-upgrade
