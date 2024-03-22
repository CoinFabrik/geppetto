import unittest

from geppetto.llm_controller import LLMController, WipGenericHandler


class HandlerMock(WipGenericHandler):

    def __init__(self, name, model):
        self.name = name
        self.model = model

    def get_info(self):
        return "LLM %s model %s" % (self.name, self.model)


sample_llms_cfg = [
    {
        "name": "First LLM",
        "model": "LLM1",
        "handler": HandlerMock
    },
    {
        "name": "Second LLM",
        "model": "LLM2",
        "handler": HandlerMock
    }
]


class TestController(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls.llm_controller = LLMController(
            sample_llms_cfg
        )

    @classmethod
    def tearDown(cls):
        cls.llm_controller = None

    def test_controller_set_up(self):
        assert len(self.llm_controller.llm_cfgs) == 2
        assert len(self.llm_controller.handlers) == 0

    def test_initialize_controller(self):
        self.llm_controller.init_controller()
        assert len(self.llm_controller.llm_cfgs) == 2
        assert len(self.llm_controller.handlers) == 2

    def test_get_llm_cfg(self):
        cfg = self.llm_controller.get_llm_cfg("Second LLM")
        assert cfg["model"] == "LLM2"

    def test_attempt_get_nonexistent_llm_cfg(self):
        self.assertRaises(
            ValueError,
            self.llm_controller.get_llm_cfg,
            "Wrong LLM"
        )

    def test_list_llms(self):
        list = self.llm_controller.list_llms()
        assert list == ["First LLM", "Second LLM"]

    def test_get_handler(self):
        handler = self.llm_controller.get_handler("Second LLM")
        self.assertIsInstance(handler, HandlerMock)

    def test_controller_handler_usage(self):
        self.llm_controller.init_controller()
        info = self.llm_controller.handlers["First LLM"].get_info()
        assert info == "LLM First LLM model LLM1"


if __name__ == "__main__":
    unittest.main()
