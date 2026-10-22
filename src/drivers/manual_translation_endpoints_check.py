"""Manual check for the two translation endpoints.

Sends real HTTP requests to a running service and exercises both translation endpoints:

    POST /translate       text in the query string
    POST /translate/text  text in a JSON body

Usage (from the repo root):

    python src/drivers/manual_translation_endpoints_check.py

    python src/drivers/manual_translation_endpoints_check.py http://localhost:5051

The service URL defaults to SERVICE_HOST + SERVICE_PORT from the environment or the .env file
at the repo root. The service itself needs OLLAMA_API_KEY (it is in the .env file at the repo
root) to answer with a real translation.

The service must be running, e.g.:

    just start
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import requests

from configuration import MAX_TRANSLATE_TEXT_CHARS, SERVICE_HOST, SERVICE_PORT

TIMEOUT = 300

SHORT_TEXT = "Device keys allow Ollama to access your account's cloud models."

LONG_TEXT = "Device keys allow Ollama to access your account's cloud models. " * 40

LANGUAGE_FROM = "en"
LANGUAGE_TO = "es"


class Check:
    def __init__(
        self,
        name: str,
        expected_status: int,
        expected_body_contains: str | None = None,
        expect_non_empty_body: bool = False,
    ):
        self.name = name
        self.expected_status = expected_status
        self.expected_body_contains = expected_body_contains
        self.expect_non_empty_body = expect_non_empty_body
        self.status: int | None = None
        self.body: str = ""
        self.error: str = ""
        self.passed = False

    def record(self, response: requests.Response) -> None:
        self.status = response.status_code
        try:
            self.body = response.json().get("translated_text", response.text)
        except ValueError:
            self.body = response.text

    def record_error(self, error: Exception) -> None:
        self.error = f"{type(error).__name__}: {error}"

    def evaluate(self) -> None:
        if self.error:
            self.passed = False
            return
        if self.status != self.expected_status:
            self.passed = False
            return
        if self.expected_body_contains is not None and self.expected_body_contains not in self.body:
            self.passed = False
            return
        if self.expect_non_empty_body and not self.body.strip():
            self.passed = False
            return
        self.passed = True


def build_service_url() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].rstrip("/")

    host = SERVICE_HOST.rstrip("/")
    port = SERVICE_PORT
    if host.endswith(f":{port}"):
        return host
    return f"{host}:{port}"


def check_service_is_up(service_url: str) -> bool:
    try:
        response = requests.get(f"{service_url}/", timeout=10)
    except requests.RequestException as error:
        print(f"Service is not reachable at {service_url}: {error}", file=sys.stderr)
        print("Start the service first, e.g. with: just start", file=sys.stderr)
        return False

    if response.status_code != 200:
        print(f"Service at {service_url} answered {response.status_code}", file=sys.stderr)
        return False

    return True


def post_query_endpoint(service_url: str, text: str, language_from: str, language_to: str) -> requests.Response:
    return requests.post(
        f"{service_url}/translate",
        params={"text": text, "language_from": language_from, "language_to": language_to},
        timeout=TIMEOUT,
    )


def post_body_endpoint(service_url: str, text: str, language_from: str, language_to: str) -> requests.Response:
    return requests.post(
        f"{service_url}/translate/text",
        json={"text": text, "language_from": language_from, "language_to": language_to},
        timeout=TIMEOUT,
    )


def run_check(check: Check, call) -> Check:
    try:
        check.record(call())
    except requests.RequestException as error:
        check.record_error(error)
    check.evaluate()
    return check


def print_check(check: Check) -> None:
    marker = "PASS" if check.passed else "FAIL"
    print(f"[{marker}] {check.name}")
    if check.error:
        print(f"       error: {check.error}")
    else:
        print(f"       status: {check.status}")
        preview = check.body if len(check.body) <= 200 else f"{check.body[:200]}..."
        print(f"       body: {preview}")


def main() -> int:
    service_url = build_service_url()
    print(f"Service: {service_url}")

    if not check_service_is_up(service_url):
        return 1

    checks = [
        run_check(
            Check(
                "POST /translate (query string) translates the text",
                expected_status=200,
                expect_non_empty_body=True,
            ),
            lambda: post_query_endpoint(service_url, SHORT_TEXT, LANGUAGE_FROM, LANGUAGE_TO),
        ),
        run_check(
            Check(
                "POST /translate/text (JSON body) translates the text",
                expected_status=200,
                expect_non_empty_body=True,
            ),
            lambda: post_body_endpoint(service_url, SHORT_TEXT, LANGUAGE_FROM, LANGUAGE_TO),
        ),
        run_check(
            Check(
                f"POST /translate/text (JSON body) accepts a long text ({len(LONG_TEXT)} chars)",
                expected_status=200,
                expect_non_empty_body=True,
            ),
            lambda: post_body_endpoint(service_url, LONG_TEXT, LANGUAGE_FROM, LANGUAGE_TO),
        ),
        run_check(
            Check(
                f"POST /translate/text (JSON body) rejects text over {MAX_TRANSLATE_TEXT_CHARS} chars",
                expected_status=400,
                expected_body_contains="maximum length",
            ),
            lambda: post_body_endpoint(service_url, "x" * (MAX_TRANSLATE_TEXT_CHARS + 1), LANGUAGE_FROM, LANGUAGE_TO),
        ),
        run_check(
            Check(
                "POST /translate (query string) rejects text over the maximum length",
                expected_status=400,
                expected_body_contains="maximum length",
            ),
            lambda: post_query_endpoint(service_url, "x" * (MAX_TRANSLATE_TEXT_CHARS + 1), LANGUAGE_FROM, LANGUAGE_TO),
        ),
        run_check(
            Check(
                "POST /translate/text (JSON body) rejects an unsupported language",
                expected_status=400,
                expected_body_contains="not supported",
            ),
            lambda: post_body_endpoint(service_url, SHORT_TEXT, LANGUAGE_FROM, "zh"),
        ),
    ]

    for check in checks:
        print_check(check)

    failed = [check for check in checks if not check.passed]
    if failed:
        print(f"\n{len(failed)} of {len(checks)} checks failed", file=sys.stderr)
        return 1

    print(f"\nAll {len(checks)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
