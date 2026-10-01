import base64
from uuid import uuid4

import httpx
from .provider import BaseProvider, AIResponse

class GigaChatProvider(BaseProvider):
    def __init__(self, client_id: str, client_secret: str, scope: str, ca_bundle: str | None = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.ca_bundle = ca_bundle
        self._token = None

    async def _get_token(self):
        credentials = self.client_secret.strip()
        try:
            decoded_credentials = base64.b64decode(credentials, validate=True).decode('utf-8')
        except (ValueError, UnicodeDecodeError):
            decoded_credentials = ''
        if not decoded_credentials.startswith(f'{self.client_id}:'):
            credentials = base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode('utf-8')).decode('ascii')
        async with httpx.AsyncClient(timeout=30.0, verify=self.ca_bundle or True) as client:
            resp = await client.post(
                'https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
                headers={'Authorization': f'Basic {credentials}', 'RqUID': str(uuid4()), 'Content-Type': 'application/x-www-form-urlencoded'},
                data={'scope': self.scope}
            )
            resp.raise_for_status()
            self._token = resp.json()['access_token']

    async def generate(self, prompt: str, system: str = '') -> AIResponse:
        if not self._token:
            await self._get_token()
        async with httpx.AsyncClient(timeout=60.0, verify=self.ca_bundle or True) as client:
            resp = await client.post(
                'https://gigachat.devices.sberbank.ru/api/v1/chat/completions',
                headers={'Authorization': f'Bearer {self._token}'},
                json={
                    'model': 'GigaChat-Pro',
                    'messages': [
                        {'role': 'system', 'content': system},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 2000
                }
            )
            resp.raise_for_status()
            data = resp.json()
            return AIResponse(
                text=data['choices'][0]['message']['content'],
                provider='gigachat',
                tokens_used=data['usage']['total_tokens'],
                model='GigaChat-Pro'
            )
