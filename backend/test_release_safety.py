import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models.sop import SOP
from seed_sops import seed_sops
from sop_catalog import CATALOGUE
from services.ai_service.gigachat import GigaChatProvider
from services.ai_service.compliance import build_evidence_report

from api.endpoints.ai import parse_model_object


class ReleaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.test_engine = create_engine(
            'sqlite://',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
        )
        self.testing_session = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        Base.metadata.create_all(bind=self.test_engine)

        def override_get_db():
            db = self.testing_session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.test_engine)
        self.test_engine.dispose()

    def seed_test_sops(self):
        with self.testing_session() as db:
            return seed_sops(db)

    def test_clinical_record_api_routes_are_removed(self):
        for path in ('/api/patients/', '/api/cards/', '/api/situations/', '/api/ai/generate-situation'):
            with self.subTest(path=path):
                response = self.client.get(path) if path != '/api/ai/generate-situation' else self.client.post(path, json={})
                self.assertEqual(response.status_code, 404)

    def test_catalog_has_88_unique_sops_and_seeds_idempotently(self):
        self.assertEqual(len(CATALOGUE), 88)
        self.assertEqual(len({key for _, key, _ in CATALOGUE}), 88)
        self.assertEqual(self.seed_test_sops(), 88)
        self.assertEqual(self.seed_test_sops(), 0)
        self.assertEqual(self.client.get('/api/sops/').status_code, 200)
        self.assertEqual(len(self.client.get('/api/sops/?limit=500').json()), 88)

    def test_catalog_drafts_are_marked_for_normative_verification(self):
        self.seed_test_sops()
        with self.testing_session() as db:
            sop = db.query(SOP).filter(SOP.key == 'emergency-recognition').one()
            self.assertEqual(sop.status, 'draft')
            self.assertIn('сверить', sop.normative_refs)
            self.assertIn('одним врачом', sop.scope)
            self.assertIn('приостановить', sop.procedure)

    def test_evidence_report_never_confirms_compliance_from_catalog_card(self):
        report = build_evidence_report({
            'status': 'found',
            'sources': [{
                'title': 'Об утверждении документа',
                'url': 'http://publication.pravo.gov.ru/document/1234567890123',
                'publication_number': '1234567890123',
                'publication_date': '01.09.2026',
            }],
        })
        self.assertFalse(report['compliance_confirmed'])
        self.assertEqual(report['status'], 'insufficient_evidence')
        self.assertEqual(report['sources'][0]['full_text_status'], 'not_retrieved')
        self.assertIsNone(report['requirements'][0]['requirement'])

    def test_checklist_templates_can_be_loaded(self):
        response = self.client.get('/api/checklists/templates')

        self.assertEqual(response.status_code, 200)
        self.assertEqual({item['key'] for item in response.json()}, {'emergency-readiness', 'cabinet-opening'})
        self.assertIn('не подтверждены', response.json()[0]['source_note'].lower())

    def test_checklist_inspection_is_saved_and_returned_in_history(self):
        template = self.client.get('/api/checklists/templates').json()[0]
        payload = {
            'template_key': template['key'],
            'responsible': 'Сотрудник клиники',
            'performed_at': '2026-10-01T10:30:00',
            'overall_note': 'Проверка для теста.',
            'items': [
                {'item_key': item[0], 'status': 'compliant', 'actual': 'Проверено', 'note': ''}
                for item in template['items']
            ],
        }
        saved = self.client.post('/api/checklists/inspections', json=payload)

        self.assertEqual(saved.status_code, 201)
        self.assertEqual(saved.json()['template_title'], template['title'])
        self.assertEqual(len(saved.json()['items']), len(template['items']))
        self.assertEqual(saved.json()['performed_at'], '2026-10-01T10:30:00')
        history = self.client.get('/api/checklists/inspections').json()
        self.assertEqual(history[0]['id'], saved.json()['id'])

    def test_checklist_inspection_rejects_missing_template_items(self):
        response = self.client.post('/api/checklists/inspections', json={
            'template_key': 'emergency-readiness',
            'responsible': 'Сотрудник клиники',
            'performed_at': '2026-10-01T10:30:00',
            'items': [{'item_key': 'emergency-contact', 'status': 'unchecked'}],
        })

        self.assertEqual(response.status_code, 422)

    def test_checklist_inspection_rejects_unchecked_items(self):
        template = self.client.get('/api/checklists/templates').json()[0]
        payload = {
            'template_key': template['key'],
            'responsible': 'Сотрудник клиники',
            'performed_at': '2026-10-01T10:30:00',
            'items': [
                {'item_key': item[0], 'status': 'unchecked', 'actual': '', 'note': ''}
                for item in template['items']
            ],
        }
        response = self.client.post('/api/checklists/inspections', json=payload)

        self.assertEqual(response.status_code, 422)

    def test_gigachat_tls_uses_default_verification_or_explicit_ca_bundle(self):
        for ca_bundle, expected in ((None, True), ('C:/trusted/organization-ca.pem', 'C:/trusted/organization-ca.pem')):
            provider = GigaChatProvider('client-id', 'secret', 'scope', ca_bundle)
            with patch('services.ai_service.gigachat.httpx.AsyncClient') as client:
                client.return_value.__aenter__.return_value.post.side_effect = RuntimeError('stop after client setup')
                try:
                    import asyncio
                    asyncio.run(provider._get_token())
                except RuntimeError:
                    pass
                client.assert_called_once()
                self.assertEqual(client.call_args.kwargs['verify'], expected)

    def test_approved_sop_cannot_be_updated_or_approved_twice(self):
        create = self.client.post('/api/sops/', json={
            'key': 'release-test', 'title': 'Тестовый СОП', 'category': 'clinical',
            'status': 'draft',
        })
        sop_id = create.json()['id']
        approved = self.client.post(
            f'/api/sops/{sop_id}/approve',
            json={'order_number': '12', 'order_date': '2026-10-01'},
        )
        update = self.client.put(f'/api/sops/{sop_id}', json={
            'key': 'release-test', 'title': 'Изменённый СОП', 'category': 'clinical',
            'status': 'draft',
        })
        approve_again = self.client.post(
            f'/api/sops/{sop_id}/approve',
            json={'order_number': '13', 'order_date': '2026-10-02'},
        )

        self.assertEqual(create.status_code, 200)
        self.assertEqual(approved.json()['order'], '12 от 01.10.2026')
        self.assertEqual(update.status_code, 409)
        self.assertEqual(approve_again.status_code, 409)

    def test_ai_generation_can_select_only_enabled_providers(self):
        from api.endpoints.ai import get_enabled_providers

        configured = ['gigachat', 'yandexgpt']

        self.assertEqual(get_enabled_providers(configured, ['gigachat']), ['gigachat'])
        self.assertEqual(get_enabled_providers(configured, ['unknown']), [])
        self.assertEqual(get_enabled_providers(configured, []), configured)
        self.assertEqual(get_enabled_providers(configured, None), configured)

    def test_parse_model_object_accepts_markdown_fenced_json(self):
        payload = '''```json
{
  "scope": "Текст",
  "normative_refs": "Ссылка",
  "terms": "Термины",
  "responsibilities": "Ответственность",
  "procedure": "Процедура",
  "quality_control": "Контроль",
  "documentation": "Документация"
}
```'''

        result = parse_model_object(payload, (
            'scope', 'normative_refs', 'terms', 'responsibilities',
            'procedure', 'quality_control', 'documentation'
        ))

        self.assertEqual(result['scope'], 'Текст')
        self.assertEqual(result['procedure'], 'Процедура')

    def test_parse_model_object_accepts_nested_json_fields(self):
        payload = '''{
  "scope": "Настоящий СОП...",
  "normative_refs": ["ГОСТ ИСО 9001", "Внутренние документы"],
  "terms": {"термин": "определение"},
  "responsibilities": {"главный врач": "ответственность"},
  "procedure": {"шаг_1": "выполнить действие"},
  "quality_control": {"контроль": "проверка"},
  "documentation": {"формы": "журнал"}
}'''

        result = parse_model_object(payload, (
            'scope', 'normative_refs', 'terms', 'responsibilities',
            'procedure', 'quality_control', 'documentation'
        ))

        self.assertEqual(result['scope'], 'Настоящий СОП...')
        self.assertEqual(result['normative_refs'], '[\n  "ГОСТ ИСО 9001",\n  "Внутренние документы"\n]')
        self.assertIn('"шаг_1": "выполнить действие"', result['procedure'])

    def test_parse_model_object_rejects_missing_required_fields(self):
        with self.assertRaises(ValueError):
            parse_model_object('{"scope": "Текст"}', ('scope', 'procedure'))

    def test_normative_refs_are_explicit_when_search_is_unavailable(self):
        from services.ai_service.legal_search import format_official_references

        result = format_official_references({'status': 'unavailable', 'queries': ['СОП'], 'sources': []})

        self.assertIn('поиск на официальном интернет-портале', result.lower())
        self.assertIn('не проверены', result.lower())

    def test_official_search_references_use_only_real_document_results(self):
        from services.ai_service.legal_search import format_official_references

        result = format_official_references({
            'status': 'found',
            'queries': ['СанПиН'],
            'sources': [{
                'title': 'Постановление Главного государственного санитарного врача РФ',
                'url': 'http://publication.pravo.gov.ru/document/0001202507250036',
                'publication_number': '0001202507250036',
                'publication_date': '25.07.2025',
            }],
        })

        self.assertIn('0001202507250036', result)
        self.assertIn('25.07.2025', result)
        self.assertIn('http://publication.pravo.gov.ru/document/', result)

    def test_official_search_parser_extracts_document_metadata(self):
        from services.ai_service.legal_search import parse_official_documents

        html = '''<div class="documents-table-row">
          <a href="/document/0001202507250036" class="documents-item-name">Постановление № 12<br />СанПиН 3.3686-21</a>
          <span class="info-name">Номер опубликования: </span><span class="info-data">0001202507250036</span>
          <span class="info-name">Дата опубликования: </span><span class="info-data">25.07.2025</span>
        </div>'''

        results = parse_official_documents(html)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['publication_number'], '0001202507250036')
        self.assertEqual(results[0]['publication_date'], '25.07.2025')
        self.assertIn('СанПиН 3.3686-21', results[0]['title'])

    def test_official_search_prioritizes_base_approving_act(self):
        from services.ai_service.legal_search import format_official_references

        references = format_official_references({
            'status': 'found',
            'queries': ['СанПиН'],
            'sources': [
                {
                    'title': 'Постановление от 2025 года № 12 "О внесении изменений в постановление № 4 "Об утверждении правил"',
                    'url': 'http://publication.pravo.gov.ru/document/amendment',
                    'publication_number': 'amendment',
                    'publication_date': '25.07.2025',
                },
                {
                    'title': 'Постановление Главного санитарного врача от 28.01.2021 № 4 "Об утверждении СанПиН 3.3686-21"',
                    'url': 'http://publication.pravo.gov.ru/document/base',
                    'publication_number': 'base',
                    'publication_date': '18.02.2021',
                },
            ],
        })

        self.assertLess(references.index('/document/base'), references.index('/document/amendment'))
        self.assertIn('применимость к этому СОП не проверены', references)