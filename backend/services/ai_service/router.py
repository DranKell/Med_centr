from .provider import BaseProvider, AIResponse
from .cache import CacheService
from .sanitizer import sanitize_document_text
import httpx
import hashlib

class AIRouter:
    def __init__(self, providers: list, cache: CacheService):
        self.providers = providers
        self.cache = cache

    async def generate(self, key: str, prompt: str, system: str = '', force_regenerate: bool = False) -> AIResponse:
        cache_key = hashlib.sha256(f'{key}\0{system}\0{prompt}'.encode('utf-8')).hexdigest()
        if not force_regenerate:
            cached = await self.cache.get(cache_key)
            if cached:
                return AIResponse(**cached, from_cache=True)

        last_error = None
        for provider in self.providers:
            try:
                response = await provider.generate(prompt, system)
                response.text = sanitize_document_text(response.text)
                await self.cache.set(cache_key, {
                    'text': response.text,
                    'provider': response.provider,
                    'tokens_used': response.tokens_used,
                    'model': response.model,
                })
                return response
            except Exception as e:
                last_error = e
                continue

        if not self.providers:
            raise RuntimeError('Не настроен ни один ИИ-провайдер.')
        raise RuntimeError(_safe_provider_error(last_error)) from last_error


def _safe_provider_error(error: Exception | None) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        return f'ИИ-провайдер отклонил запрос (HTTP {error.response.status_code}). Проверьте ключи, scope и доступ к модели.'
    if isinstance(error, httpx.TimeoutException):
        return 'Истекло время ожидания ответа ИИ-провайдера. Проверьте сеть и повторите попытку.'

    message = str(error or '')
    if 'CERTIFICATE_VERIFY_FAILED' in message or 'self-signed certificate' in message.lower():
        return 'TLS-соединение с ИИ-провайдером не прошло проверку сертификата: в цепочке есть недоверенный сертификат. Проверьте цепочку сертификатов VPN/прокси и добавьте доверенный CA в хранилище Python. Проверка TLS остаётся включённой.'
    if isinstance(error, httpx.ConnectError):
        return 'Не удалось установить защищённое соединение с ИИ-провайдером. Проверьте сеть, VPN/прокси и TLS-сертификаты.'
    return f'Ошибка ИИ-провайдера ({type(error).__name__}). Проверьте журнал backend.'
