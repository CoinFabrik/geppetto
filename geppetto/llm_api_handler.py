from abc import ABC, abstractmethod
from typing import Callable


class LLMHandler(ABC):
    def __init__(self, name, model, client):
        self.name = name
        self.model = model
        self.client = client

    def get_info(self):
        return f"Name: {self.name} - Model: {self.model}"

    @abstractmethod
    def llm_generate_content(self, prompt: str, callback: Callable, *callback_args):
        pass