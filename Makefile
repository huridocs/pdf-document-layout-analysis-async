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
	docker compose --profile production up --build

stop:
	docker compose --profile testing stop

start-test:
	docker compose --profile testing up --attach api-pdf-layout --attach queue-processor-pdf-layout --attach worker-pdf-layout --build

start_detached:
	docker compose --profile testing up --build -d

upgrade:
	. .venv/bin/activate; pip-upgrade
