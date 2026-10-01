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