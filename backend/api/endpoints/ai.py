import json
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from services.ai_service.router import AIRouter
from services.ai_service.prompts import APP_SYSTEM
from services.ai_service.cache import CacheService
from services.ai_service.legal_search import format_official_references, search_official_documents
from services.ai_service.sanitizer import sanitize_document_text
from services.ai_service.compliance import build_evidence_report

router = APIRouter()

SOP_FIELDS = (
    'scope', 'normative_refs', 'terms', 'responsibilities', 'procedure',
    'quality_control', 'documentation',
)


def get_enabled_providers(configured: list[str], enabled_names: list[str] | None) -> list[str]:
    if not enabled_names:
        return configured
    enabled_set = {name.strip().lower() for name in enabled_names if name and name.strip()}
    if not enabled_set:
        return configured
    return [name for name in configured if name.lower() in enabled_set]


def get_ai_router(enabled_names: list[str] | None = None) -> AIRouter:
    from config import settings
    from services.ai_service.gigachat import GigaChatProvider
    from services.ai_service.yandexgpt import YandexGPTProvider

    configured = []
    ca_bundle = settings.SSL_CERT_FILE or None
    if settings.GIGACHAT_CLIENT_ID and settings.GIGACHAT_CLIENT_SECRET:
        configured.append('gigachat')
    if settings.YANDEX_IAM_TOKEN:
        configured.append('yandexgpt')

    providers = []
    if 'gigachat' in get_enabled_providers(configured, enabled_names):
        providers.append(GigaChatProvider(settings.GIGACHAT_CLIENT_ID, settings.GIGACHAT_CLIENT_SECRET, settings.GIGACHAT_SCOPE, ca_bundle))
    if 'yandexgpt' in get_enabled_providers(configured, enabled_names):
        providers.append(YandexGPTProvider(settings.YANDEX_IAM_TOKEN, settings.YANDEX_FOLDER_ID, settings.YANDEX_MODEL_URI, ca_bundle))

    cache = CacheService()
    return AIRouter(providers, cache)


def parse_model_object(text: str, required_fields: tuple[str, ...]) -> dict:
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.IGNORECASE)

    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and start < end:
        cleaned = cleaned[start:end + 1]

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError('AI response does not match the requested document schema') from error

    if not isinstance(result, dict):
        raise ValueError('AI response does not match the requested document schema')

    if any(not isinstance(result.get(field), (str, list, dict)) for field in required_fields):
        raise ValueError('AI response does not match the requested document schema')

    for field in required_fields:
        value = result[field]
        if isinstance(value, (dict, list)):
            result[field] = json.dumps(value, ensure_ascii=False, indent=2)
    return result

# --- Генерация СОП ---
SOP_SYSTEM = APP_SYSTEM

SOP_PROMPT = '''Подготовь проект СОП только для конкретной темы «{title}» и категории «{category}».

Входные данные:
- Ссылки пользователя: {normative_refs}
- Карточки публикаций, найденные на Официальном интернет-портале правовой информации: {official_sources}

Правила поиска и доказательности:
1. Используй только сведения, относящиеся непосредственно к теме СОП. Не подменяй тему общими правилами клиники.
2. Нормативные акты, номера, даты, пункты, сроки, режимы, концентрации, дозировки и критерии включай только если они прямо есть в переданных ссылках или карточках. Ничего не выдумывай и не достраивай по памяти.
3. Карточка публикации подтверждает только факт найденной публикации, но не её действующую редакцию и применимость. В normative_refs перечисли только переданные реквизиты и явно укажи необходимость проверки.
4. Если источники не найдены или недостаточны, прямо напиши это и сформулируй шаги только на безопасном организационном уровне: кто что проверяет, где сверяет инструкцию, когда останавливает процесс и кому сообщает.

Требования к содержанию:
- procedure должен быть предметным алгоритмом именно для «{title}»: конкретные действия персонала по шагам, подготовка рабочего места, проверка до начала, последовательность операции, критерий перехода, критерии остановки, действия при отклонении, завершение и запись результата.
- Не начинай procedure шаблоном «Идентифицировать ситуацию и открыть локальную карту». Не используй пустые фразы «выполнить процедуру согласно СОП» или «действовать по инструкции» без описания действия.
- Не приписывай клинике оборудование, должности, ассистента или полномочия, которых нет во входных данных. Учитывай модель одного врача.
- responsibilities раздели по фактически доступным ролям; не создавай роль ассистента, если она не указана.
- quality_control должен содержать проверяемые признаки результата и порядок действий при несоответствии без выдуманных числовых нормативов.
- documentation укажи конкретную запись: дата/время, объект или пациент, результат, отклонение, действие и подпись.
- Это проект до медицинской, юридической и локальной проверки; не выдавай его за утверждённый документ.

Верни СТРОГО JSON с ключами: scope, normative_refs, terms, responsibilities, procedure, quality_control, documentation. Значения — строки. Без Markdown и текста вне JSON.'''

class GenerateSopRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    category: str = Field(default='emergency', max_length=100)
    normative_refs: str = Field(default='', max_length=3000)
    enabled_providers: list[str] | None = Field(default=None, max_items=10)

@router.post('/generate-sop')
async def generate_sop(req: GenerateSopRequest):
    title = sanitize_document_text(req.title)
    category = sanitize_document_text(req.category)
    normative_refs = sanitize_document_text(req.normative_refs)
    try:
        from config import settings
        if not settings.EXTERNAL_AI_ENABLED:
            raise HTTPException(status_code=503, detail='Внешний ИИ отключён настройкой EXTERNAL_AI_ENABLED.')

        source_search = await search_official_documents(
            [title, normative_refs],
            ca_bundle=settings.SSL_CERT_FILE or None,
            category=category,
        )
        official_sources = '\n'.join(
            f"- {source['title']} | опубликовано {source['publication_number']} от {source['publication_date']} | {source['url']}"
            for source in source_search['sources']
        ) or f"Статус официального поиска: {source_search['status']}"
        prompt = SOP_PROMPT.format(
            title=title,
            category=category,
            normative_refs=normative_refs or 'не указаны',
            official_sources=official_sources,
        )

        ai = get_ai_router(req.enabled_providers)
        response = await ai.generate(key='sop', prompt=prompt, system=SOP_SYSTEM)
        text = sanitize_document_text(response.text)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    try:
        parsed = parse_model_object(text, SOP_FIELDS)
        parsed['normative_refs'] = format_official_references(source_search, normative_refs)
        text = json.dumps(parsed, ensure_ascii=False, indent=2)
    except (ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail='ИИ ответил в некорректном формате. Текущий текст СОПа не изменён.') from error

    evidence_report = build_evidence_report(source_search, normative_refs)
    return {
        'text': text,
        'provider': response.provider,
        'from_cache': response.from_cache,
        'normative_search': source_search,
        'evidence_report': evidence_report,
        'compliance_confirmed': False,
        'fallback': False,
        'draft': True,
        'warning': 'Черновик ИИ. Требуется проверка ответственным специалистом.',
    }
