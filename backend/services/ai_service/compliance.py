"""Evidence inventory, not an automated legal opinion."""
from datetime import datetime, timezone
import re
from urllib.parse import urlsplit


def build_evidence_report(search_result: dict, user_references: str = '') -> dict:
    sources = []
    requirements = []
    seen = set()
    for source in search_result.get('sources', []):
        url = source.get('url', '')
        try:
            address = urlsplit(url)
            trusted = (
                address.scheme in ('http', 'https')
                and address.hostname == 'publication.pravo.gov.ru'
                and address.username is None
                and address.password is None
                and address.port in (None, 80, 443)
                and re.fullmatch(r'/document/\d+/?', address.path) is not None
                and not address.query and not address.fragment
            )
        except ValueError:
            trusted = False
        number = source.get('publication_number', '')
        try:
            datetime.strptime(source.get('publication_date', ''), '%d.%m.%Y')
            valid_date = True
        except (ValueError, TypeError):
            valid_date = False
        valid = bool(trusted and source.get('title', '').strip()
                     and re.fullmatch(r'\d+', number) and valid_date
                     and address.path.rstrip('/').split('/')[-1] == number)
        identity = url.rstrip('/')
        if identity in seen:
            continue
        seen.add(identity)
        source_id = f'S{len(sources) + 1}'
        sources.append({
            'id': source_id, **{key: source.get(key, '') for key in
                              ('title', 'url', 'publication_number', 'publication_date')},
            'metadata_status': 'consistent' if valid else 'rejected',
            'full_text_status': 'not_retrieved',
            'validity_status': 'not_checked',
            'applicability_status': 'not_checked',
        })
        if valid:
            requirements.append({
                'source_id': source_id, 'clause': None, 'quotation': None,
                'requirement': None, 'staff_action': None, 'control': None,
                'record': None, 'status': 'needs_full_text_and_review',
            })
    gaps = ['Полные тексты и пункты актов не проверены.',
            'Действующая редакция, вступление в силу и переходные положения не проверены.',
            'Применимость к лицензии, оснащению и персоналу клиники не проверена.',
            'Полнота перечня обязательных требований не подтверждена.']
    if not requirements:
        gaps.insert(0, 'Нет карточек с согласованными официальными реквизитами.')
    if any(s['metadata_status'] == 'rejected' for s in sources):
        gaps.append('Есть отклонённые карточки источников; не использовать их при генерации.')
    return {
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'search_status': search_result.get('status', 'unavailable'),
        'status': 'insufficient_evidence', 'compliance_confirmed': False,
        'sources': sources, 'requirements': requirements, 'gaps': gaps,
        'user_references': {'text': user_references, 'status': 'not_verified'},
        'warning': 'Проверена только согласованность реквизитов; это не подтверждение законодательства или соответствия СОП.',
    }
