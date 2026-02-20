from configuration import LANGUAGES_SHORT, LANGUAGES
from domain.TranslationTask import TranslationTask


def get_content(translation_task: TranslationTask):
    language_to_name = "English"
    languages_to = [x for x in LANGUAGES_SHORT if translation_task.language_to.lower()[:2] == x]

    if languages_to:
        language_to_name = LANGUAGES[LANGUAGES_SHORT.index(languages_to[0])]

    content = f"""Please translate the following text into {language_to_name}. Follow these guidelines:
1. Maintain the original layout and formatting.
2. Translate all text accurately without omitting any part of the content.
3. Preserve the tone and style of the original text.
4. Do not include any additional comments, notes, or explanations in the output; provide only the translated text.
5. Only translate the text between ``` and ```. Do not output any other text or character.

Here is the text to be translated:
"""
    content += "\n\n" + "```" + translation_task.text + "```"
    return content


def get_translation(translation_task: TranslationTask) -> Translation:
    ip_address = MlCloudConnector(ServerType.TRANSLATION, service_logger).get_ip()
    client = Client(host=f"http://{ip_address}:{TRANSLATIONS_PORT}")

    service_logger.info(f"Using translation model {MODEL} on ip {ip_address}")
    content = get_content(translation_task)
    pull_model(client)

    response = client.chat(model=MODEL, messages=[{"role": "user", "content": content}])
    response_content = response["message"]["content"]
    if response_content.startswith("```") and response_content.endswith("```"):
        response_content = response_content[3:-3]

    return Translation(
        text=response_content,
        language=translation_task.language_to,
        success=True,
        error_message="",
    )
