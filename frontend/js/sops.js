const SOP_CATEGORIES = {
    emergency: 'Неотложные состояния',
    'infection-control': 'Инфекционная безопасность',
    sterilization: 'Очистка и стерилизация',
    sanitary: 'Санитарный режим',
    'medical-waste': 'Медицинские отходы',
    equipment: 'Оборудование и укладки',
    'clinical-safety': 'Безопасность медицинской деятельности',
    'clinic-organization': 'Организация клиники'
};

function escapeSOPHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, function(character) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character];
    });
}

function formatSOPField(value, fieldKey) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (!trimmed || /^-?\s*(?:\[\]|\{\})$/.test(trimmed)) return '';
        if (trimmed[0] === '[' || trimmed[0] === '{') {
            try {
                return formatSOPField(JSON.parse(trimmed), fieldKey);
            } catch (error) {
                return trimmed;
            }
        }
        return trimmed.split(/\r?\n/).filter(function(line) {
            return !/^-?\s*(?:\[\]|\{\})$/.test(line.trim());
        }).join('\n');
    }
    if (Array.isArray(value)) {
        return value.map(function(item) {
            return formatSOPField(item, fieldKey);
        }).filter(Boolean).join('\n');
    }
    if (typeof value === 'object') {
        return Object.entries(value).map(function(entry) {
            const content = formatSOPField(entry[1], fieldKey);
            if (!content) return '';
            if (fieldKey === 'normative_refs') return content;
            return entry[0] + ': ' + content;
        }).filter(Boolean).join('\n');
    }
    return String(value);
}

const SOPEditor = {
    currentId: null,
    fields: [
        { key: 'scope', label: '1. Область применения' },
        { key: 'normative_refs', label: '2. Нормативные ссылки' },
        { key: 'terms', label: '3. Термины и определения' },
        { key: 'responsibilities', label: '4. Ответственность' },
        { key: 'procedure', label: '5. Процедура (пошагово)' },
        { key: 'quality_control', label: '6. Контроль качества' },
        { key: 'documentation', label: '7. Документирование' }
    ],
    async api(path, opts) {
        const r = await fetch(API_BASE + '/api/sops' + path, opts);
        if (!r.ok) throw new Error('SOP API error ' + r.status);
        return r.json();
    },
    async loadList() {
        try {
            const arr = await this.api('/');
            const cat = document.getElementById('sop-filter').value;
            const filtered = cat ? arr.filter(function(s) { return s.category === cat; }) : arr;
            document.getElementById('sops-list').innerHTML = filtered.map(function(s) {
                const badge = s.status === 'approved'
                    ? '<span class="badge badge-ok">Утверждён' + (s.approval_order ? ' · ' + escapeSOPHTML(s.approval_order) : '') + '</span>'
                    : '<span class="badge badge-draft">🟡 Черновик</span>';
                return '<div class="situation-card sop-item" onclick="SOPEditor.open(' + Number(s.id) + ')"><h3>СОП №' + escapeSOPHTML(s.number || '—') + '. ' + escapeSOPHTML(s.title) + '</h3>' + badge + '<p>' + escapeSOPHTML(SOP_CATEGORIES[s.category] || s.category) + '</p></div>';
            }).join('') || '<p>Пока нет СОПов.</p>';
        } catch (e) { alert('Backend не подключён: ' + e.message); }
    },
    async open(id) {
        try {
            const s = await this.api('/' + id);
            this.currentId = s.id;
            this.renderCard(s, s.status === 'draft');
        } catch (e) { alert('Ошибка: ' + e.message); }
    },
    newSop() {
        this.currentId = null;
        this.renderCard({ title: '', number: '', category: 'clinic-organization', status: 'draft' }, true);
    },
    renderCard(s, editable) {
        const panel = document.getElementById('sop-card');
        const badge = s.status === 'approved'
            ? '<span class="badge badge-ok">Утверждён' + (s.approval_order ? ' · ' + escapeSOPHTML(s.approval_order) : '') + '</span>'
            : '<span class="badge badge-draft">🟡 Черновик</span>';
        let html = '<h3>СОП №' + escapeSOPHTML(s.number || '—') + '. ' + escapeSOPHTML(s.title || 'Новый СОП') + '</h3>' + badge;
        html += '<div class="sop-meta no-print"><label>Название:<input id="sop-title" value="' + escapeSOPHTML(s.title || '') + '"' + (editable ? '' : ' readonly') + '></label>';
        html += '<label>Номер:<input id="sop-number" value="' + escapeSOPHTML(s.number || '') + '"' + (editable ? '' : ' readonly') + '></label>';
        html += '<label>Категория:<select id="sop-category"' + (editable ? '' : ' disabled') + '>';
        for (const k in SOP_CATEGORIES) html += '<option value="' + k + '"' + (s.category === k ? ' selected' : '') + '>' + SOP_CATEGORIES[k] + '</option>';
        html += '</select></label></div>';
        this.fields.forEach(function(f) {
            html += '<div class="sop-field"><label>' + f.label + '</label><textarea id="sop-f-' + f.key + '"' + (editable ? '' : ' readonly') + '>' + escapeSOPHTML(formatSOPField(s[f.key], f.key)) + '</textarea></div>';
        });
        html += '<div class="sop-actions no-print">';
        if (editable) {
            html += '<button class="btn btn-primary" id="generate-sop-ai-btn" onclick="SOPEditor.generateAI()">🤖 Сгенерировать через ИИ</button>';
            html += '<span id="ai-generation-status" class="ai-generation-status no-print" role="status" aria-live="polite" hidden></span>';
            html += '<button class="btn btn-success" onclick="SOPEditor.save()">💾 Сохранить</button>';
            html += '<button class="btn btn-secondary" onclick="window.print()">Печать проекта и листа ознакомления</button>';
            if (this.currentId) html += '<button class="btn btn-secondary" onclick="SOPEditor.showApprovalForm()">Утвердить приказом</button>';
        } else {
            html += '<button class="btn btn-primary" onclick="window.print()">Печать СОПа и листа ознакомления</button>';
            html += '<button class="btn btn-secondary" onclick="SOPEditor.newRevision()">✏️ Создать редакцию</button>';
        }
        html += '</div>';
        if (s.status === 'approved' && editable) {
            html += '<div id="approval-form" class="approval-form no-print">';
            html += '<h4>Утверждение приказом</h4><label>Номер приказа<input id="approval-order-number" maxlength="40" required></label>';
            html += '<label>Дата приказа<input id="approval-order-date" type="date" required></label>';
            html += '<button class="btn btn-success" onclick="SOPEditor.submitApproval()">Подтвердить утверждение</button></div>';
        } else if (editable && this.currentId) {
            html += '<div id="approval-form" class="approval-form no-print" hidden>';
            html += '<h4>Утверждение приказом</h4><label>Номер приказа<input id="approval-order-number" maxlength="40" required></label>';
            html += '<label>Дата приказа<input id="approval-order-date" type="date" required></label>';
            html += '<button class="btn btn-success" onclick="SOPEditor.submitApproval()">Подтвердить утверждение</button></div>';
        }
        html += this.renderPrintSheet(s);
        panel.innerHTML = html;
    },
    renderPrintSheet(s) {
        const signRows = Array.from({ length: 12 }, function(_, index) {
            return '<tr><td>' + (index + 1) + '</td><td></td><td></td><td></td><td></td></tr>';
        }).join('');
        return '<section class="sop-print-sheet"><h2>Лист ознакомления</h2>' +
            '<p><strong>СОП:</strong> ' + escapeSOPHTML(s.title || '') + '</p>' +
            '<p><strong>Номер:</strong> ' + escapeSOPHTML(s.number || 'не присвоен') + '</p>' +
            '<p><strong>Статус:</strong> ' + (s.status === 'approved' ? 'Утверждён приказом ' + escapeSOPHTML(s.approval_order || '') : 'Проект. Не утверждён') + '</p>' +
            '<table><thead><tr><th>№</th><th>Фамилия, имя, отчество</th><th>Должность</th><th>Дата</th><th>Подпись</th></tr></thead><tbody>' + signRows + '</tbody></table>' +
            '<p class="print-note">Лист заполняется после утверждения документа и фактического ознакомления сотрудника.</p></section>';
    },
    collect() {
        const data = { title: document.getElementById('sop-title').value, number: document.getElementById('sop-number').value, category: document.getElementById('sop-category').value };
        this.fields.forEach(function(f) { data[f.key] = document.getElementById('sop-f-' + f.key).value; });
        return data;
    },
    async generateAI() {
        const title = document.getElementById('sop-title').value;
        if (!title) { alert('Сначала впиши название СОП'); return; }
        const category = document.getElementById('sop-category').value;
        const enabledProviders = LocalData.getEnabledAIProviders();
        const button = document.getElementById('generate-sop-ai-btn');
        const status = document.getElementById('ai-generation-status');
        const originalLabel = button.textContent;
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        button.innerHTML = '<span class="ai-spinner" aria-hidden="true"></span> ИИ генерирует СОП…';
        status.hidden = false;
        status.className = 'ai-generation-status is-loading no-print';
        status.textContent = enabledProviders.length
            ? 'Отправляю запрос через ' + enabledProviders.map(function(name) { return name === 'gigachat' ? 'GigaChat' : 'YandexGPT'; }).join(', ') + '. Обычно это занимает несколько секунд.'
            : 'Оба ИИ отключены. Включите GigaChat или YandexGPT в шапке.';

        try {
            if (!enabledProviders.length) {
                throw new Error('Оба ИИ отключены. Включите хотя бы один провайдер в шапке.');
            }
            const r = await fetch(API_BASE + '/api/ai/generate-sop', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: title, category: category, enabled_providers: enabledProviders }) });
            const data = await r.json().catch(function() { return {}; });
            if (!r.ok) {
                throw new Error(data.detail || 'Сервер вернул ошибку HTTP ' + r.status + '.');
            }
            if (data.fallback || data.provider === 'local-template') {
                throw new Error(data.warning || 'ИИ недоступен. Локальный пустой черновик не подставлен.');
            }
            const result = typeof data.text === 'string' ? JSON.parse(data.text) : data.text;
            if (!result || this.fields.some(function(field) { return typeof result[field.key] !== 'string'; })) {
                throw new Error('ИИ вернул ответ, который не соответствует структуре СОПа. Текущий текст не изменён.');
            }
            this.fields.forEach(function(field) {
                const input = document.getElementById('sop-f-' + field.key);
                if (input) input.value = formatSOPField(result[field.key], field.key);
            });
            status.className = 'ai-generation-status is-success no-print';
            status.textContent = 'Черновик получен от ' + (data.provider || 'ИИ') + (data.from_cache ? ' (из кэша)' : '') + '. Проверьте нормативные ссылки и весь текст.';
        } catch (error) {
            status.className = 'ai-generation-status is-error no-print';
            status.textContent = 'Генерация не выполнена: ' + error.message;
            if (/TLS|сертификат|certificate/i.test(error.message)) {
                const help = document.createElement('a');
                help.href = 'certificates.html';
                help.textContent = 'Сертификат Минцифры для Python';
                help.className = 'certificate-help-link';
                status.appendChild(document.createElement('br'));
                status.appendChild(help);
            }
        } finally {
            button.disabled = false;
            button.removeAttribute('aria-busy');
            button.textContent = originalLabel;
        }
    },
    async save() {
        const data = this.collect();
        if (!data.title) { alert('Впиши название СОП'); return; }
        data.key = 'sop_' + (this.currentId || Date.now());
        data.status = 'draft';
        try {
            if (this.currentId) {
                await this.api('/' + this.currentId, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            } else {
                const created = await this.api('/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
                this.currentId = created.id;
            }
            alert('СОП сохранён (черновик)');
            this.loadList();
        } catch (e) { alert('Ошибка сохранения: ' + e.message); }
    },
    showApprovalForm() {
        const form = document.getElementById('approval-form');
        if (form) form.hidden = false;
        document.getElementById('approval-order-number')?.focus();
    },
    async submitApproval() {
        const num = document.getElementById('approval-order-number')?.value.trim();
        const date = document.getElementById('approval-order-date')?.value;
        if (!num || !date) {
            alert('Укажите номер и дату приказа.');
            return;
        }
        try {
            await this.api('/' + this.currentId + '/approve', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order_number: num, order_date: date }) });
            alert('Приказ зарегистрирован. Статус СОПа утверждён.');
            this.open(this.currentId);
            this.loadList();
        } catch (e) { alert('Ошибка: ' + e.message); }
    },
    async newRevision() {
        const s = await this.api('/' + this.currentId);
        const copy = { key: s.key + '_rev' + Date.now(), number: s.number, title: s.title + ' (новая редакция)', category: s.category, normative_refs: s.normative_refs, scope: s.scope, terms: s.terms, responsibilities: s.responsibilities, procedure: s.procedure, quality_control: s.quality_control, documentation: s.documentation, status: 'draft' };
        const created = await this.api('/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(copy) });
        this.currentId = created.id;
        this.renderCard(created, true);
        this.loadList();
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const btn = document.querySelector('[data-tab="sops"]');
    if (btn) btn.addEventListener('click', function() { SOPEditor.loadList(); });
});
