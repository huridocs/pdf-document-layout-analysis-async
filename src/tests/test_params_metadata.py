import json
from typing import Any, Dict, Union
from unittest import TestCase

from pydantic import TypeAdapter

from domain.Params import Params
from domain.ResultMessage import ResultMessage
from domain.Task import Task
from domain.TranslationTaskMessage import TranslationTaskMessage

# Same union shape the queue consumer validates against
adapter = TypeAdapter(Union[TranslationTaskMessage, Task])


def build_failed_result(task: Task) -> ResultMessage:
    return ResultMessage(tenant=task.tenant, task=task.task, params=task.params, success=False, error_message="x")


def parse(payload: dict):
    return adapter.validate_python(payload)


class TestMetadataPassthrough(TestCase):
    def test_task_without_metadata_omits_the_key(self):
        task = Task(tenant="t1", task="ocr", params=Params(filename="a.pdf", language="en"))

        self.assertIsNone(task.params.metadata)
        self.assertNotIn("metadata", json.loads(task.model_dump_json())["params"])

    def test_task_with_metadata_roundtrips_unchanged(self):
        metadata: Dict[str, Any] = {"key": "abc:2", "count": 3, "nested": {"a": [1, 2]}}
        payload = {
            "tenant": "t1",
            "task": "ocr",
            "params": {"filename": "a.pdf", "language": "en", "metadata": metadata},
        }

        parsed = parse(payload)

        self.assertIsInstance(parsed, Task)
        self.assertEqual(metadata, parsed.params.metadata)
        roundtripped = json.loads(parsed.params.model_dump_json())["metadata"]
        self.assertEqual(metadata, roundtripped)

    def test_non_dict_metadata_is_accepted(self):
        task = Task(tenant="t1", task="ocr", params=Params(filename="a.pdf", metadata=["a", 1]))

        self.assertEqual(["a", 1], json.loads(task.model_dump_json())["params"]["metadata"])

    def test_success_result_message_carries_metadata(self):
        params = Params(filename="a.pdf", language="en", metadata={"key": "abc:2"})

        result = ResultMessage(tenant="t1", task="ocr", params=params, success=True, file_url="http://url")

        self.assertEqual({"key": "abc:2"}, json.loads(result.model_dump_json())["params"]["metadata"])

    def test_failed_result_message_carries_metadata(self):
        params = Params(filename="a.pdf", language="en", metadata={"key": "abc:2"})
        result = build_failed_result(Task(tenant="t1", task="segmentation", params=params))

        dumped = json.loads(result.model_dump_json())
        self.assertEqual({"key": "abc:2"}, dumped["params"]["metadata"])
        self.assertIn("error_message", dumped)

    def test_task_without_metadata_still_parses_from_raw_message(self):
        task = parse({"tenant": "t1", "task": "segmentation", "params": {"filename": "a.pdf", "language": "fr"}})

        self.assertIsInstance(task, Task)
        self.assertNotIn("metadata", json.loads(task.model_dump_json())["params"])

    def test_translation_messages_are_not_affected(self):
        payload = {"key": "abc:2", "text": "hello", "language_from": "en", "languages_to": ["es", "fr"]}

        parsed = parse(payload)

        self.assertIsInstance(parsed, TranslationTaskMessage)
