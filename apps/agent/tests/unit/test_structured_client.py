import pytest
from pydantic import BaseModel

from agent.model.structured import StructuredOutputError, async_structured_call


class Tiny(BaseModel):
    value: str


class FakeLLM:
    def __init__(self, contents):
        self.contents = list(contents)
        self.calls = 0

    async def ainvoke(self, messages, **kwargs):
        self.calls += 1

        class Msg:
            content = self.contents[min(self.calls - 1, len(self.contents) - 1)]

        return Msg()


async def test_returns_validated_model():
    llm = FakeLLM(['{"value": "ok"}'])
    out = await async_structured_call(llm=llm, system="s", user="u", response_model=Tiny)
    assert out.value == "ok"


async def test_retries_once_on_invalid_json():
    llm = FakeLLM(["not json", '{"value": "ok"}'])
    out = await async_structured_call(llm=llm, system="s", user="u", response_model=Tiny)
    assert out.value == "ok"
    assert llm.calls == 2


async def test_raises_after_retry():
    llm = FakeLLM(["not json", "still not json"])
    with pytest.raises(StructuredOutputError):
        await async_structured_call(llm=llm, system="s", user="u", response_model=Tiny)
