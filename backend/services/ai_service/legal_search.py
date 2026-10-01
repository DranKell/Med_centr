from html.parser import HTMLParser
import re
from datetime import datetime
from urllib.parse import urljoin

import httpx


OFFICIAL_PORTAL = 'http://publication.pravo.gov.ru'
SEARCH_URL = f'{OFFICIAL_PORTAL}/Documents/search'
CATEGORY_SEARCH_TERMS = {
    'infection-control': ['СанПиН 3.3686-21'],
    'sterilization': ['СанПиН 3.3686-21'],
    'sanitary': ['СанПиН 2.1.3684-21'],
    'medical-waste': ['СанПиН 2.1.3684-21'],
}


def _is_approving_document(title: str) -> bool:
    match = re.search(r'№\s*\d+\s*"([^"\n]+)', title)
    return bool(match and match.group(1).lstrip().startswith('Об утверждении'))


class OfficialDocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.documents = []
        self._current = None
        self._capture = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get('class', '').split())

        if tag == 'a' and 'documents-item-name' in classes:
            href = attributes.get('href', '')
            if href.startswith('/document/'):
                self._finish_document()
                self._current = {'title_parts': [], 'url': urljoin(OFFICIAL_PORTAL, href)}
                self._capture = 'title'
        elif self._current and tag == 'span' and 'info-name' in classes:
            self._capture = 'label'
            self._label_parts = []
        elif self._current and tag == 'span' and 'info-data' in classes:
            self._capture = 'value'
            self._value_parts = []
        elif self._capture == 'title' and tag == 'br':
            self._current['title_parts'].append(' ')

    def handle_endtag(self, tag):
        if self._capture == 'title' and tag == 'a' and self._current:
            title = ' '.join(''.join(self._current.pop('title_parts')).split())
            self._current['title'] = title
            self._capture = None
        elif self._capture == 'label' and tag == 'span':
            self._label = ' '.join(''.join(self._label_parts).split()).rstrip(':').lower()
            self._capture = None
        elif self._capture == 'value' and tag == 'span':
            value = ' '.join(''.join(self._value_parts).split())
            if 'номер опубликования' in self._label:
                self._current['publication_number'] = value
            elif 'дата опубликования' in self._label:
                self._current['publication_date'] = value
            self._capture = None

    def handle_data(self, data):
        if not self._current or not self._capture:
            return
        if self._capture == 'title':
            self._current['title_parts'].append(data)
        elif self._capture == 'label':
            self._label_parts.append(data)
        elif self._capture == 'value':
            self._value_parts.append(data)

    def close(self):
        super().close()
        self._finish_document()

    def _finish_document(self):
        if self._current and self._current.get('title'):
            self.documents.append(self._current)
        self._current = None
        self._capture = None


def parse_official_documents(html: str, limit: int = 5) -> list[dict[str, str]]:
    parser = OfficialDocumentParser()
    parser.feed(html)
    parser.close()
    unique = {}
    for document in parser.documents:
        title = document.get('title', '').strip()
        url = document.get('url', '')
        if title and url.startswith(f'{OFFICIAL_PORTAL}/document/'):
            unique[url] = {
                'title': title,
                'url': url,
                'publication_number': document.get('publication_number', ''),
                'publication_date': document.get('publication_date', ''),
            }
    return list(unique.values())[:limit]


async def search_official_documents(
    queries: list[str],
    ca_bundle: str | None = None,
    category: str = '',
) -> dict:
    topic_queries = []
    for query in queries:
        if not query or not query.strip():
            continue
        cleaned_query = re.sub(
            r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b',
            ' ',
            query,
        )
        cleaned_query = ' '.join(cleaned_query.split())[:200]
        if cleaned_query:
            topic_queries.append(cleaned_query)
    topic_queries = list(dict.fromkeys(topic_queries))
    category_queries = CATEGORY_SEARCH_TERMS.get(category, [])[:1]
    query_limit = 3 if category_queries else 3
    normalized_queries = list(dict.fromkeys(topic_queries[:query_limit - len(category_queries)] + category_queries))
    if not normalized_queries:
        return {'status': 'not_found', 'queries': [], 'sources': []}

    sources = []
    errors = []
    try:
        async with httpx.AsyncClient(timeout=15.0, verify=ca_bundle or True, follow_redirects=True) as client:
            for query in normalized_queries:
                try:
                    response = await client.get(
                        SEARCH_URL,
                        params={'Name': query, 'index': '1', 'pageSize': '10'},
                        headers={'User-Agent': 'DentalClinicSOP/1.0'},
                    )
                    response.raise_for_status()
                    parsed_sources = parse_official_documents(response.text, limit=30)
                    if not parsed_sources and 'Документы не найдены' not in response.text:
                        errors.append(query)
                    sources.extend(parsed_sources)
                except httpx.HTTPError:
                    errors.append(query)
    except httpx.HTTPError:
        return {'status': 'unavailable', 'queries': normalized_queries, 'sources': []}

    unique_sources = {source['url']: source for source in sources}
    results = sorted(
        unique_sources.values(),
        key=lambda source: (
            not _is_approving_document(source['title']),
            -datetime.strptime(source['publication_date'], '%d.%m.%Y').timestamp()
            if source.get('publication_date') else 0,
        ),
    )[:8]
    if results:
        status = 'found'
    elif errors:
        status = 'unavailable'
    else:
        status = 'not_found'
    return {'status': status, 'queries': normalized_queries, 'sources': results}


def format_official_references(search_result: dict, user_references: str = '') -> str:
    lines = []
    if search_result['status'] == 'found':
        sources = sorted(
            search_result['sources'],
            key=lambda source: (
                not _is_approving_document(source['title']),
                -datetime.strptime(source['publication_date'], '%d.%m.%Y').timestamp()
                if source.get('publication_date') else 0,
            ),
        )
        for source in sources:
            details = []
            if source.get('publication_number'):
                details.append(f"номер опубликования {source['publication_number']}")
            if source.get('publication_date'):
                details.append(f"дата {source['publication_date']}")
            suffix = f" ({'; '.join(details)})" if details else ''
            lines.append(f"{source['title']}{suffix} — {source['url']}")
        lines.append('Найденные публикации являются кандидатами; актуальность и применимость к этому СОП не проверены.')
    elif search_result['status'] == 'unavailable':
        lines.append('Поиск на Официальном интернет-портале правовой информации недоступен. Нормативные источники не проверены.')
    else:
        query = '; '.join(search_result.get('queries', []))
        lines.append(f'На Официальном интернет-портале правовой информации документы по запросу «{query}» не найдены.')

    if user_references:
        lines.append(f'Ссылки пользователя, требуют проверки: {user_references.strip()}')
    return '\n'.join(lines)