const API_BASE = '';
const API = {
    async checkBackend() {
        try {
            const r = await fetch(API_BASE + '/health');
            if (r.ok) { document.getElementById('backend-status').textContent = 'Подключен'; document.getElementById('backend-status').style.color = '#48bb78'; return true; }
        } catch (e) { document.getElementById('backend-status').textContent = 'Не подключен'; document.getElementById('backend-status').style.color = '#f56565'; return false; }
        return false;
    },
    async getSops(category) {
        if (!await this.checkBackend()) throw new Error('Backend недоступен');
        const query = category ? '?category=' + encodeURIComponent(category) : '';
        const response = await fetch(API_BASE + '/api/sops/' + query);
        if (!response.ok) throw new Error('Не удалось получить СОПы');
        return response.json();
    },
    async getChecklistTemplates() {
        const response = await fetch(API_BASE + '/api/checklists/templates');
        if (!response.ok) throw new Error('Не удалось загрузить шаблоны проверок');
        return response.json();
    },
    async getChecklistInspections() {
        const response = await fetch(API_BASE + '/api/checklists/inspections?limit=200');
        if (!response.ok) throw new Error('Не удалось загрузить историю проверок');
        return response.json();
    },
    async getChecklistInspection(id) {
        const response = await fetch(API_BASE + '/api/checklists/inspections/' + encodeURIComponent(id));
        if (!response.ok) throw new Error('Не удалось открыть проверку');
        return response.json();
    },
    async createChecklistInspection(payload) {
        const response = await fetch(API_BASE + '/api/checklists/inspections', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error('Не удалось сохранить проверку');
        return response.json();
    }
};