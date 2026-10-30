"""Offline LlamaIndex adapters for the opt-in server demo."""

from llama_index.core import Settings
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms import ChatMessage, ChatResponse, CompletionResponse, LLMMetadata
from llama_index.core.llms.custom import CustomLLM
from llama_index.core.node_parser import SentenceSplitter

from .demo_fixture import complete_fixture, embed


class DemoEmbedding(BaseEmbedding):
    def _get_text_embedding(self, text):
        return embed(text)

    def _get_query_embedding(self, query):
        return embed(query)

    async def _aget_query_embedding(self, query):
        return embed(query)


class DemoLLM(CustomLLM):
    @property
    def metadata(self):
        return LLMMetadata(context_window=16384, num_output=2048, model_name="demo-fixture-v1")

    def complete(self, prompt, **kwargs):
        return CompletionResponse(text=complete_fixture(prompt))

    async def acomplete(self, prompt, **kwargs):
        return self.complete(prompt, **kwargs)

    def stream_complete(self, prompt, **kwargs):
        response = self.complete(prompt, **kwargs)
        yield CompletionResponse(text=response.text, delta=response.text)

    def chat(self, messages, **kwargs):
        prompt = "\n".join(message.content or "" for message in messages)
        return ChatResponse(message=ChatMessage(role="assistant", content=complete_fixture(prompt)))


def configure_demo_settings():
    """Configure both models and tokenization without network access."""
    Settings.llm = DemoLLM()
    Settings.embed_model = DemoEmbedding(model_name="demo-token-hash-64-v1")
    Settings.tokenizer = lambda text: text.split()
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=0, tokenizer=Settings.tokenizer)
