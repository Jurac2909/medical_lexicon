import asyncio
import unittest

from app.logger import log_exceptions


class TestLogExceptions(unittest.TestCase):
    def test_returns_value_on_success(self):
        @log_exceptions
        def ok():
            return 42

        self.assertEqual(ok(), 42)

    def test_reraises_and_logs(self):
        @log_exceptions
        def boom():
            raise ValueError("bad")

        with self.assertLogs("medical_ner", level="ERROR"):
            with self.assertRaises(ValueError):
                boom()

    def test_reraise_false_swallows_and_returns_none(self):
        @log_exceptions(reraise=False)
        def boom():
            raise ValueError("bad")

        with self.assertLogs("medical_ner", level="ERROR"):
            self.assertIsNone(boom())

    def test_preserves_function_name(self):
        @log_exceptions
        def my_func():
            return None

        self.assertEqual(my_func.__name__, "my_func")

    def test_async_reraises_and_logs(self):
        @log_exceptions
        async def boom():
            raise KeyError("bad")

        with self.assertLogs("medical_ner", level="ERROR"):
            with self.assertRaises(KeyError):
                asyncio.run(boom())

    def test_async_reraise_false(self):
        @log_exceptions(reraise=False)
        async def boom():
            raise KeyError("bad")

        with self.assertLogs("medical_ner", level="ERROR"):
            self.assertIsNone(asyncio.run(boom()))

    def test_async_success_returns_value(self):
        @log_exceptions
        async def ok():
            return "done"

        self.assertEqual(asyncio.run(ok()), "done")


if __name__ == "__main__":
    unittest.main()
