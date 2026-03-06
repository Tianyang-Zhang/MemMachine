from unittest.mock import MagicMock, patch

import openai
import pytest
from pydantic import SecretStr

from memmachine_server.common.configuration.language_model_conf import (
    AmazonBedrockLanguageModelConf,
    LanguageModelsConf,
    OpenAIChatCompletionsLanguageModelConf,
    OpenAIResponsesLanguageModelConf,
)
from memmachine_server.common.resource_manager.language_model_manager import (
    LanguageModelManager,
)


@pytest.fixture
def mock_conf():
    """Mock LanguageModelsConf with dummy configurations."""
    conf = LanguageModelsConf(
        openai_responses_language_model_confs={
            "openai_4o_mini": OpenAIResponsesLanguageModelConf(
                model="gpt-4o-mini",
                api_key=SecretStr("DUMMY_OPENAI_API_KEY_1"),
            ),
            "openai_3_5_turbo": OpenAIResponsesLanguageModelConf(
                model="gpt-3.5-turbo",
                api_key=SecretStr("DUMMY_OPENAI_API_KEY_2"),
            ),
        },
        amazon_bedrock_language_model_confs={
            "aws_model": AmazonBedrockLanguageModelConf(
                region="us-west-2",
                aws_access_key_id=SecretStr("DUMMY_AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=SecretStr("DUMMY_AWS_SECRET_ACCESS_KEY"),
                model_id="amazon.titan-embed-text-v2:0",
                additional_model_request_fields={},
            ),
        },
        openai_chat_completions_language_model_confs={
            "ollama_model": OpenAIChatCompletionsLanguageModelConf(
                model="llama3",
                api_key=SecretStr("DUMMY_OLLAMA_API_KEY"),
                base_url="http://localhost:11434/v1",
            ),
        },
    )
    return conf


@pytest.mark.asyncio
async def test_build_open_ai_model(mock_conf):
    builder = LanguageModelManager(mock_conf)
    await builder.build_all()

    assert "openai_4o_mini" in builder._language_models
    assert "openai_3_5_turbo" in builder._language_models

    model = builder.get_language_model("openai_4o_mini")
    assert model is not None


@pytest.mark.asyncio
async def test_build_aws_bedrock_model(mock_conf):
    builder = LanguageModelManager(mock_conf)
    await builder.build_all()

    assert "aws_model" in builder._language_models

    model = builder.get_language_model("aws_model")
    assert model is not None


@pytest.mark.asyncio
async def test_build_openai_chat_completions_model(mock_conf):
    builder = LanguageModelManager(mock_conf)
    await builder.build_all()

    assert "ollama_model" in builder._language_models

    model = builder.get_language_model("ollama_model")
    assert model is not None


@pytest.mark.asyncio
async def test_build_openai_oauth_responses_model_adds_account_header():
    conf = LanguageModelsConf(
        openai_responses_language_model_confs={
            "openai_codex_oauth": OpenAIResponsesLanguageModelConf(
                model="gpt-5.3-codex",
                api_key=SecretStr("oauth-access-token"),
                auth_mode="oauth",
                oauth_account_id="account_123",
            )
        }
    )

    with patch("openai.AsyncOpenAI", spec=openai.AsyncOpenAI) as mock_async_openai:
        builder = LanguageModelManager(conf)
        await builder.build_all()

    kwargs = mock_async_openai.call_args.kwargs
    assert kwargs["api_key"] == "oauth-access-token"
    assert kwargs["base_url"] == "https://chatgpt.com/backend-api/codex"
    assert kwargs["default_headers"] == {"ChatGPT-Account-Id": "account_123"}


@pytest.mark.asyncio
async def test_build_openai_oauth_responses_model_refreshes_expired_token():
    conf = LanguageModelsConf(
        openai_responses_language_model_confs={
            "openai_codex_oauth": OpenAIResponsesLanguageModelConf(
                model="gpt-5.3-codex",
                api_key=SecretStr(""),
                auth_mode="oauth",
                oauth_refresh_token=SecretStr("refresh-token"),
                oauth_client_id=SecretStr("client-id"),
                oauth_expires_at=1,
            )
        }
    )

    refresh_response = MagicMock()
    refresh_response.raise_for_status.return_value = None
    refresh_response.json.return_value = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 3600,
    }

    with (
        patch("httpx.post", return_value=refresh_response) as mock_httpx_post,
        patch("openai.AsyncOpenAI", spec=openai.AsyncOpenAI) as mock_async_openai,
    ):
        builder = LanguageModelManager(conf)
        await builder.build_all()

    kwargs = mock_async_openai.call_args.kwargs
    assert kwargs["api_key"] == "new-access-token"
    assert kwargs["base_url"] == "https://chatgpt.com/backend-api/codex"
    mock_httpx_post.assert_called_once()

    built_conf = conf.openai_responses_language_model_confs["openai_codex_oauth"]
    assert built_conf.api_key.get_secret_value() == "new-access-token"
    assert built_conf.oauth_refresh_token is not None
    assert built_conf.oauth_refresh_token.get_secret_value() == "new-refresh-token"
    assert built_conf.oauth_expires_at is not None
