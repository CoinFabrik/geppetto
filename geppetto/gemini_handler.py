from io import BytesIO
import json
from PIL import Image
from urllib.request import urlopen
import logging

from .exceptions import InvalidThreadFormatError
from .llm_api_handler import LLMHandler
from dotenv import load_dotenv
from typing import List, Dict
import os
import textwrap
import google.generativeai as genai
from IPython.display import display
from IPython.display import Markdown

load_dotenv(os.path.join("config", ".env"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL=os.getenv("GEMINI_MODEL")
MSG_FIELD = "parts"
MSG_INPUT_FIELD = "content"

def to_markdown(text):
    text = text.replace('•', '  *')
    return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

class GeminiHandler(LLMHandler):

    def __init__(
        self,
        personality,
    ):
        super().__init__(
            'Gemini',
            GEMINI_MODEL,
            genai.GenerativeModel(GEMINI_MODEL),
        )
        self.personality = personality
        self.system_role = "system"
        self.assistant_role = "model"
        self.user_role = "user"
        genai.configure(api_key=GOOGLE_API_KEY)

    def llm_generate_content(self, user_prompt, status_callback=None, *status_callback_args):
        logging.info("Sending msg to gemini: %s" % user_prompt)
        response= self.client.generate_content(user_prompt)
        markdown_response = to_markdown(response.text)
        return str(markdown_response.data)
    
    def get_prompt_from_thread(self, thread: List[Dict], assistant_tag: str, user_tag: str):
        prompt = super().get_prompt_from_thread(thread, assistant_tag, user_tag)
        for msg in prompt:
            if MSG_INPUT_FIELD in msg:
                msg[MSG_FIELD] = [msg.pop(MSG_INPUT_FIELD)]
            else:
                raise InvalidThreadFormatError("The input thread doesn't have the field %s" % MSG_INPUT_FIELD)
        return prompt
