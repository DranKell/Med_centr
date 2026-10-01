import httpx
from .provider import BaseProvider, AIResponse

class YandexGPTProvider(BaseProvider):
    def __init__(self, iam_token: str, folder_id: str, model_uri: str, ca_bundle: str | None = None):
        self.iam_token = iam_token
        self.folder_id = folder_id
        self.model_uri = model_uri
        self.ca_bundle = ca_bundle

    async def generate(self, prompt: str, system: str = '') -> AIResponse:
        async with httpx.AsyncClient(timeout=60.0, verify=self.ca_bundle or True) as client:
            resp = await client.post(
                'https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
                headers={'Authorization': f'Bearer {self.iam_token}', 'x-folder-id': self.folder_id},
                json={
                    'modelUri': self.model_uri,
                    'completionOptions': {'stream': False, 'temperature': 0.3, 'maxTokens': '2000'},
                    'messages': [
                        {'role': 'system', 'text': system},
                        {'role': 'user', 'text': prompt}
                    ]
                }
            )
            resp.raise_for_status()
            data = resp.json()
            return AIResponse(
                text=data['result']['alternatives'][0]['message']['text'],
                provider='yandexgpt',
                tokens_used=int(data['result']['usage']['totalTokens']),
                model='YandexGPT'
            )
