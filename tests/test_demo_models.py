"""LlamaIndex adapter checks; require the project's Python dependencies."""

from unittest.mock import patch

from llama_index.core import Settings
from llama_index.core.llms import ChatMessage

from graphrag_anthropic_llamaindex.demo_models import DemoLLM
from graphrag_anthropic_llamaindex.server import GraphRAGService


def test_demo_configuration_never_constructs_external_models():
    previous = (Settings._llm, Settings._embed_model, Settings._node_parser, Settings._tokenizer)
    try:
        with patch("graphrag_anthropic_llamaindex.server.Anthropic", side_effect=AssertionError), \
             patch("graphrag_anthropic_llamaindex.server.HuggingFaceEmbedding", side_effect=AssertionError), \
             patch("graphrag_anthropic_llamaindex.server.BedrockConverse", side_effect=AssertionError), \
             patch("graphrag_anthropic_llamaindex.server.ClaudeCodeLLM", side_effect=AssertionError):
            GraphRAGService._configure_settings({"llm_provider": "demo"})
            assert isinstance(Settings.llm, DemoLLM)
            assert len(Settings.embed_model.get_text_embedding("AlopexDB")) == 64
            response = Settings.llm.chat([ChatMessage(role="user", content="## Context Information: AlopexDB\n## User Question: details")])
            assert "AlopexDB" in response.message.content
    finally:
        Settings._llm, Settings._embed_model, Settings._node_parser, Settings._tokenizer = previous
