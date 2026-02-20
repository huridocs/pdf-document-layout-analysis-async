import json
import time
from unittest import TestCase

from rsmq import RedisSMQ

from domain.TranslationResponseMessage import TranslationResponseMessage
from domain.TranslationTaskMessage import TranslationTaskMessage

QUEUE = RedisSMQ(host="127.0.0.1", port="6379", qname="translations_tasks")


class TestEndToEnd(TestCase):
    def test_translations(self):
        task = TranslationTaskMessage(key=["key", "1"], text="Hola", language_from="es", languages_to=["en", "fr"])

        QUEUE.sendMessage(delay=0).message(task.model_dump_json()).execute()

        results_message = self.get_results_message()

        self.assertEqual(["key", "1"], results_message.key)
        self.assertEqual("Hola", results_message.text)
        self.assertEqual("es", results_message.language_from)
        self.assertEqual(["en", "fr"], results_message.languages_to)
        self.assertEqual(2, len(results_message.translations))

        en_translation = [translation for translation in results_message.translations if translation.language == "en"][0]
        self.assertEqual(True, en_translation.success)
        self.assertEqual("", en_translation.error_message)
        self.assertNotEqual("", en_translation.text)

        fr_translation = [translation for translation in results_message.translations if translation.language == "fr"][0]
        self.assertEqual(True, fr_translation.success)
        self.assertEqual("", fr_translation.error_message)
        self.assertNotEqual("", fr_translation.text)

    @staticmethod
    def get_results_message() -> TranslationResponseMessage:
        for i in range(20):
            time.sleep(3)
            queue = RedisSMQ(host="127.0.0.1", port="6379", qname="translations_results", quiet=True)

            message = queue.receiveMessage().exceptions(False).execute()
            if message:
                queue.deleteMessage(id=message["id"]).execute()
                return TranslationResponseMessage(**json.loads(message["message"]))

        raise Exception("No message found")
