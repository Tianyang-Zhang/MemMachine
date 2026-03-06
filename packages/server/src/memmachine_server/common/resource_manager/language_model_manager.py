"""Builder for LanguageModel instances."""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any

import httpx
from pydantic import SecretStr

from memmachine_server.common.configuration.language_model_conf import (
    AmazonBedrockLanguageModelConf,
    LanguageModelsConf,
    OpenAIChatCompletionsLanguageModelConf,
    OpenAIResponsesLanguageModelConf,
)
from memmachine_server.common.errors import InvalidLanguageModelError
from memmachine_server.common.language_model.language_model import LanguageModel
from memmachine_server.common.resource_manager.base_manager import BaseResourceManager

logger = logging.getLogger(__name__)

OPENAI_OAUTH_REFRESH_SKEW_SECONDS = 60


class LanguageModelManager(BaseResourceManager[LanguageModel]):
    """Create and cache configured language model instances."""

    def __init__(self, conf: LanguageModelsConf) -> None:
        """Store configuration and initialize caches."""
        super().__init__()
        self.conf = conf
        # Alias for backward compatibility
        self._language_models = self._resources

    @property
    def _resource_type_name(self) -> str:
        return "language model"

    def _is_configured(self, name: str) -> bool:
        """Check if a language model is configured."""
        return (
            name in self.conf.openai_responses_language_model_confs
            or name in self.conf.openai_chat_completions_language_model_confs
            or name in self.conf.amazon_bedrock_language_model_confs
        )

    def _get_not_found_error(self, name: str) -> Exception:
        """Return InvalidLanguageModelError for unknown language models."""
        return InvalidLanguageModelError(f"Language model with name {name} not found.")

    def get_all_names(self) -> set[str]:
        """Return all configured language model names."""
        names = set()
        names.update(self.conf.openai_responses_language_model_confs)
        names.update(self.conf.openai_chat_completions_language_model_confs)
        names.update(self.conf.amazon_bedrock_language_model_confs)
        return names

    async def build_all(self) -> dict[str, LanguageModel]:
        """Build all configured language models and return the cache."""
        return await self.build_all_with_error_tracking(self.get_all_names())

    async def get_language_model(
        self, name: str, validate: bool = False
    ) -> LanguageModel:
        """Return a named language model, building it on first access."""
        return await self._get_resource_with_locking(name, validate=validate)

    async def _build_resource(self, name: str, validate: bool = False) -> LanguageModel:
        """Build a language model by name."""
        return await self._build_language_model(name, validate=validate)

    def remove_language_model(self, name: str) -> bool:
        """
        Remove a language model from the manager.

        Returns True if the model was removed, False if it wasn't found.
        """
        removed = self._remove_from_cache(name)
        # Also remove from config
        if name in self.conf.openai_responses_language_model_confs:
            del self.conf.openai_responses_language_model_confs[name]
            removed = True
        if name in self.conf.openai_chat_completions_language_model_confs:
            del self.conf.openai_chat_completions_language_model_confs[name]
            removed = True
        if name in self.conf.amazon_bedrock_language_model_confs:
            del self.conf.amazon_bedrock_language_model_confs[name]
            removed = True
        return removed

    def add_language_model_config(
        self,
        name: str,
        provider: str,
        config: OpenAIResponsesLanguageModelConf
        | OpenAIChatCompletionsLanguageModelConf
        | AmazonBedrockLanguageModelConf,
    ) -> None:
        """
        Add a new language model configuration at runtime.

        Args:
            name: The name/id for the language model.
            provider: The provider type ('openai-responses', 'openai-chat-completions', 'amazon-bedrock').
            config: The provider-specific configuration object.

        """
        # Clear any previous errors for this name
        self.clear_build_error(name)

        if provider == "openai-responses":
            from memmachine_server.common.configuration.language_model_conf import (
                OpenAIResponsesLanguageModelConf,
            )

            if not isinstance(config, OpenAIResponsesLanguageModelConf):
                raise ValueError(
                    "Expected OpenAIResponsesLanguageModelConf for provider 'openai-responses'"
                )
            self.conf.openai_responses_language_model_confs[name] = config
        elif provider == "openai-chat-completions":
            from memmachine_server.common.configuration.language_model_conf import (
                OpenAIChatCompletionsLanguageModelConf,
            )

            if not isinstance(config, OpenAIChatCompletionsLanguageModelConf):
                raise ValueError(
                    "Expected OpenAIChatCompletionsLanguageModelConf for provider 'openai-chat-completions'"
                )
            self.conf.openai_chat_completions_language_model_confs[name] = config
        elif provider == "amazon-bedrock":
            from memmachine_server.common.configuration.language_model_conf import (
                AmazonBedrockLanguageModelConf,
            )

            if not isinstance(config, AmazonBedrockLanguageModelConf):
                raise ValueError(
                    "Expected AmazonBedrockLanguageModelConf for provider 'amazon-bedrock'"
                )
            self.conf.amazon_bedrock_language_model_confs[name] = config
        else:
            raise ValueError(f"Unknown language model provider: {provider}")

    @staticmethod
    async def _validate_language_model(
        name: str, language_model: LanguageModel
    ) -> None:
        """Validate that the language model is working."""
        try:
            logger.info("Validating language model '%s' ...", name)
            _ = await language_model.generate_response(
                system_prompt="a",
                user_prompt="b",
            )
            logger.info("Language model '%s' is valid.", name)
        except Exception as e:
            raise InvalidLanguageModelError(
                f"language model '{name}' is invalid. {e}"
            ) from e

    async def _build_language_model(
        self, name: str, validate: bool = False
    ) -> LanguageModel:
        """Construct a language model based on provider."""
        ret: LanguageModel | None = None
        if name in self.conf.openai_responses_language_model_confs:
            ret = self._build_openai_responses_language_model(name)
        if name in self.conf.openai_chat_completions_language_model_confs:
            ret = self._build_openai_chat_completions_language_model(name)
        if name in self.conf.amazon_bedrock_language_model_confs:
            ret = self._build_amazon_bedrock_language_model(name)
        if ret is None:
            raise InvalidLanguageModelError(
                f"Language model with name {name} not found."
            )
        if validate:
            await self._validate_language_model(name, ret)
        return ret

    @staticmethod
    def _get_optional_secret_value(secret: SecretStr | None) -> str | None:
        """Return trimmed SecretStr value or None when unset/empty."""
        if secret is None:
            return None
        value = secret.get_secret_value().strip()
        return value or None

    @staticmethod
    def _decode_jwt_claims(access_token: str) -> object | None:
        """Decode JWT-like payload section into claims object."""
        token_parts = access_token.split(".")
        if len(token_parts) < 2:
            return None

        payload_segment = token_parts[1]
        padding = "=" * ((4 - len(payload_segment) % 4) % 4)
        try:
            decoded = base64.urlsafe_b64decode((payload_segment + padding).encode())
            return json.loads(decoded)
        except Exception:
            return None

    @staticmethod
    def _search_account_id_in_claims(claims: object) -> str | None:
        """Search nested JWT claims for account id keys."""
        stack: list[object] = [claims]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for key, value in node.items():
                    normalized_key = str(key).strip().lower()
                    if normalized_key in {
                        "accountid",
                        "account_id",
                        "chatgptaccountid",
                        "chatgpt_account_id",
                    } and isinstance(value, str):
                        candidate = value.strip()
                        if candidate:
                            return candidate
                    stack.append(value)
            elif isinstance(node, list):
                stack.extend(node)
        return None

    @classmethod
    def _extract_openai_account_id_from_access_token(
        cls,
        access_token: str,
    ) -> str | None:
        """Best-effort extraction of account id claim from JWT-like access token."""
        claims = cls._decode_jwt_claims(access_token)
        if claims is None:
            return None
        return cls._search_account_id_in_claims(claims)

    def _refresh_openai_oauth_access_token(
        self,
        *,
        refresh_token: str,
        client_id: str,
        token_url: str,
    ) -> tuple[str, str, int | None]:
        """Refresh OpenAI OAuth access token via refresh_token grant."""
        try:
            response = httpx.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                },
                headers={"Accept": "application/json"},
                timeout=20.0,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as err:
            raise InvalidLanguageModelError(
                "Failed to refresh OpenAI OAuth token for openai-responses language model."
            ) from err

        access_token_raw = payload.get("access_token")
        access_token = (
            access_token_raw.strip() if isinstance(access_token_raw, str) else ""
        )
        if not access_token:
            raise InvalidLanguageModelError(
                "OpenAI OAuth token refresh succeeded but no access_token was returned."
            )

        refresh_token_raw = payload.get("refresh_token")
        next_refresh_token = (
            refresh_token_raw.strip()
            if isinstance(refresh_token_raw, str) and refresh_token_raw.strip()
            else refresh_token
        )

        expires_at: int | None = None
        expires_at_raw = payload.get("expires_at")
        if isinstance(expires_at_raw, int | float):
            expires_at = int(expires_at_raw)
        else:
            expires_in_raw = payload.get("expires_in")
            if isinstance(expires_in_raw, int | float):
                expires_at = int(time.time()) + int(expires_in_raw)

        return access_token, next_refresh_token, expires_at

    def _resolve_openai_oauth_credentials(
        self,
        conf: OpenAIResponsesLanguageModelConf,
    ) -> tuple[str, dict[str, str]]:
        """Resolve OAuth access token and headers for OpenAI Codex auth mode."""
        access_token = conf.api_key.get_secret_value().strip()
        refresh_token = self._get_optional_secret_value(conf.oauth_refresh_token)
        client_id = self._get_optional_secret_value(conf.oauth_client_id)
        expires_at = conf.oauth_expires_at

        should_refresh = bool(
            refresh_token
            and client_id
            and (
                not access_token
                or (
                    isinstance(expires_at, int)
                    and int(time.time())
                    >= (expires_at - OPENAI_OAUTH_REFRESH_SKEW_SECONDS)
                )
            )
        )
        if should_refresh:
            refreshed_access_token, refreshed_refresh_token, refreshed_expires_at = (
                self._refresh_openai_oauth_access_token(
                    refresh_token=refresh_token,
                    client_id=client_id,
                    token_url=conf.oauth_token_url,
                )
            )
            access_token = refreshed_access_token
            conf.api_key = SecretStr(refreshed_access_token)
            conf.oauth_refresh_token = SecretStr(refreshed_refresh_token)
            conf.oauth_expires_at = refreshed_expires_at

        if not access_token:
            raise InvalidLanguageModelError(
                "OpenAI OAuth auth_mode requires an access token in api_key "
                "or a refresh-token+client-id pair."
            )

        account_id = (
            conf.oauth_account_id
            or self._extract_openai_account_id_from_access_token(access_token)
        )
        if account_id and conf.oauth_account_id is None:
            conf.oauth_account_id = account_id

        headers: dict[str, str] = {}
        if account_id:
            headers["ChatGPT-Account-Id"] = account_id

        return access_token, headers

    def _build_openai_responses_language_model(self, name: str) -> LanguageModel:
        import openai

        from memmachine_server.common.language_model.openai_responses_language_model import (
            OpenAIResponsesLanguageModel,
            OpenAIResponsesLanguageModelParams,
        )

        conf = self.conf.openai_responses_language_model_confs[name]

        client_api_key = conf.api_key.get_secret_value()
        default_headers: dict[str, str] | None = None
        if conf.auth_mode == "oauth":
            client_api_key, resolved_headers = self._resolve_openai_oauth_credentials(
                conf
            )
            if resolved_headers:
                default_headers = resolved_headers

        client_kwargs: dict[str, Any] = {
            "api_key": client_api_key,
            "base_url": conf.base_url,
        }
        if default_headers:
            client_kwargs["default_headers"] = default_headers

        return OpenAIResponsesLanguageModel(
            OpenAIResponsesLanguageModelParams(
                client=openai.AsyncOpenAI(**client_kwargs),
                model=conf.model,
                max_retry_interval_seconds=conf.max_retry_interval_seconds,
                metrics_factory=conf.get_metrics_factory(),
                user_metrics_labels=conf.user_metrics_labels,
                store=conf.store,
            ),
        )

    def _build_openai_chat_completions_language_model(self, name: str) -> LanguageModel:
        import openai

        from memmachine_server.common.language_model.openai_chat_completions_language_model import (
            OpenAIChatCompletionsLanguageModel,
            OpenAIChatCompletionsLanguageModelParams,
        )

        conf = self.conf.openai_chat_completions_language_model_confs[name]

        return OpenAIChatCompletionsLanguageModel(
            OpenAIChatCompletionsLanguageModelParams(
                client=openai.AsyncOpenAI(
                    api_key=conf.api_key.get_secret_value(),
                    base_url=conf.base_url,
                ),
                model=conf.model,
                max_retry_interval_seconds=conf.max_retry_interval_seconds,
                metrics_factory=conf.get_metrics_factory(),
                user_metrics_labels=conf.user_metrics_labels,
            ),
        )

    def _build_amazon_bedrock_language_model(self, name: str) -> LanguageModel:
        import boto3
        from botocore.config import Config

        from memmachine_server.common.language_model.amazon_bedrock_language_model import (
            AmazonBedrockLanguageModel,
            AmazonBedrockLanguageModelParams,
        )

        conf = self.conf.amazon_bedrock_language_model_confs[name]

        def _get_secret_value(secret: SecretStr | None) -> str | None:
            if secret is None:
                return None
            return secret.get_secret_value()

        client = boto3.client(
            "bedrock-runtime",
            region_name=conf.region,
            aws_access_key_id=_get_secret_value(conf.aws_access_key_id),
            aws_secret_access_key=_get_secret_value(conf.aws_secret_access_key),
            aws_session_token=_get_secret_value(conf.aws_session_token),
            config=Config(
                retries={
                    "total_max_attempts": 1,
                    "mode": "standard",
                },
            ),
        )

        return AmazonBedrockLanguageModel(
            AmazonBedrockLanguageModelParams(
                client=client,
                model_id=conf.model_id,
                inference_config=conf.inference_config,
                additional_model_request_fields=conf.additional_model_request_fields,
                max_retry_interval_seconds=conf.max_retry_interval_seconds,
                metrics_factory=conf.get_metrics_factory(),
                user_metrics_labels=conf.user_metrics_labels,
            ),
        )
