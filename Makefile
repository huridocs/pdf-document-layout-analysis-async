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
	docker compose stop ; docker compose -f docker-compose-test.yml stop

start-test:
	docker compose  -f docker-compose-test.yml up --attach api-pdf-layout --attach queue-processor-pdf-layout --build

start_detached:
	docker compose  -f docker-compose-test.yml up --build -d

upgrade:
	. .venv/bin/activate; pip-upgrade

free_up_space:
	df -h
	sudo rm -rf /usr/share/dotnet
	sudo rm -rf /usr/local/lib/android
	sudo rm -rf /opt/hostedtoolcache/CodeQL
	sudo rm -rf /opt/ghc
	sudo rm -rf "/usr/local/share/boost"
	sudo rm -rf "$AGENT_TOOLSDIRECTORY"
	sudo rm -rf "/opt/hostedtoolcache/boost"
	sudo apt-get remove -y '^llvm-.*' || true
	sudo apt-get remove -y 'php.*' || true
	sudo apt-get remove -y google-cloud-sdk hhvm google-chrome-stable firefox mono-devel || true
	sudo apt-get autoremove -y
	sudo apt-get clean
	sudo rm -rf /usr/share/dotnet
	sudo rm -rf /usr/local/lib/android
	sudo rm -rf /opt/hostedtoolcache/CodeQL
	sudo docker image prune --all --force
	df -h
