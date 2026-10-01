const ChecklistEditor = {
    templates: [],
    inspections: [],
    activeTemplate: null,
    activeInspection: null,
    statusLabels: {
        compliant: 'Соответствует',
        non_compliant: 'Не соответствует',
        not_applicable: 'Не применимо',
        unchecked: 'Не проверено'
    },

    async init() {
        try {
            const [templates, inspections] = await Promise.all([
                API.getChecklistTemplates(),
                API.getChecklistInspections()
            ]);
            this.templates = templates;
            this.inspections = inspections;
            this.renderTemplateOptions();
            this.renderHistory();
            if (this.templates.length) this.startNew();
            document.getElementById('checklist-new-btn').addEventListener('click', () => this.startNew());
            document.getElementById('checklist-template-select').addEventListener('change', () => this.startNew());
        } catch (error) {
            document.getElementById('checklist-workspace').innerHTML = '<p class="checklist-error">Не удалось загрузить чек-листы. Проверьте подключение backend и обновите страницу.</p>';
        }
    },

    renderTemplateOptions() {
        const select = document.getElementById('checklist-template-select');
        select.innerHTML = this.templates.map((template) =>
            '<option value="' + escapeChecklistHTML(template.key) + '">' + escapeChecklistHTML(template.title) + '</option>'
        ).join('');
    },

    renderHistory() {
        const target = document.getElementById('checklist-history');
        if (!this.inspections.length) {
            target.innerHTML = '<p class="muted">Сохранённых проверок пока нет.</p>';
            return;
        }
        target.innerHTML = this.inspections.map((inspection) => {
            const date = new Date(inspection.performed_at).toLocaleString('ru-RU');
            return '<button type="button" class="inspection-history-item" data-inspection-id="' + inspection.id + '">' +
                '<strong>' + escapeChecklistHTML(inspection.template_title) + '</strong>' +
                '<span>' + escapeChecklistHTML(date) + '</span>' +
                '<span>' + escapeChecklistHTML(inspection.responsible) + '</span></button>';
        }).join('');
        target.querySelectorAll('[data-inspection-id]').forEach((button) => {
            button.addEventListener('click', () => this.openInspection(Number(button.dataset.inspectionId)));
        });
    },

    startNew() {
        const key = document.getElementById('checklist-template-select').value;
        this.activeTemplate = this.templates.find((template) => template.key === key);
        this.activeInspection = null;
        if (this.activeTemplate) this.renderForm();
    },

    async openInspection(id) {
        try {
            const inspection = await API.getChecklistInspection(id);
            this.activeInspection = inspection;
            this.activeTemplate = this.templates.find((template) => template.key === inspection.template_key);
            document.getElementById('checklist-template-select').value = inspection.template_key;
            this.renderForm(inspection);
        } catch (error) {
            alert('Не удалось открыть сохранённую проверку.');
        }
    },

    renderForm(inspection) {
        const template = this.activeTemplate;
        const resultByKey = new Map((inspection?.items || []).map((item) => [item.item_key, item]));
        const performedAt = inspection ? inspection.performed_at.slice(0, 16) : new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
        const rows = template.items.map((item, index) => {
            const result = resultByKey.get(item[0]) || { status: 'unchecked', actual: '', note: '' };
            return '<article class="checklist-item" data-item-key="' + escapeChecklistHTML(item[0]) + '">' +
                '<div class="checklist-item-heading"><span class="checklist-index">' + (index + 1) + '</span><div><h4>' + escapeChecklistHTML(item[1]) + '</h4><p>' + escapeChecklistHTML(item[2]) + '</p><small>Основание для сверки: ' + escapeChecklistHTML(item[3]) + '</small></div></div>' +
                '<div class="checklist-item-fields"><label>Результат<select class="item-status">' + Object.entries(this.statusLabels).map(([value, label]) => '<option value="' + value + '"' + (result.status === value ? ' selected' : '') + '>' + label + '</option>').join('') + '</select></label>' +
                '<label>Фактическое состояние<input class="item-actual" type="text" maxlength="1000" value="' + escapeChecklistHTML(result.actual || '') + '" placeholder="Наблюдаемое наличие, количество или состояние"></label>' +
                '<label>Замечание / действие<textarea class="item-note" rows="2" maxlength="2000" placeholder="Что устранить, кто отвечает, срок по локальному решению">' + escapeChecklistHTML(result.note || '') + '</textarea></label></div></article>';
        }).join('');
        const readOnly = Boolean(inspection);
        const title = inspection ? 'Сохранённая проверка #' + inspection.id : 'Новая проверка';
        const overall = inspection?.overall_note || '';
        document.getElementById('checklist-workspace').innerHTML =
            '<div class="checklist-document" id="checklist-print-area">' +
            '<div class="checklist-document-head"><div><p class="eyebrow">ПРОТОКОЛ ПРОВЕРКИ</p><h3>' + escapeChecklistHTML(template.title) + '</h3><p>' + escapeChecklistHTML(template.description) + '</p></div><span class="draft-stamp">' + (inspection ? 'СОХРАНЕНО' : 'НЕ СОХРАНЕНО') + '</span></div>' +
            '<div class="checklist-source"><strong>Источники:</strong> ' + escapeChecklistHTML(template.source_note) + '</div>' +
            '<div class="checklist-meta"><label>Ответственный<input id="checklist-responsible" type="text" maxlength="200" value="' + escapeChecklistHTML(inspection?.responsible || '') + '" placeholder="Фамилия, имя, должность"' + (readOnly ? ' readonly' : '') + ' required></label>' +
            '<label>Дата и время<input id="checklist-datetime" type="datetime-local" value="' + escapeChecklistHTML(performedAt) + '"' + (readOnly ? ' readonly' : '') + ' required></label></div>' +
            '<div class="checklist-items">' + rows + '</div>' +
            '<label class="checklist-overall">Общее заключение / комментарий<textarea id="checklist-overall-note" rows="3" maxlength="5000"' + (readOnly ? ' readonly' : '') + '>' + escapeChecklistHTML(overall) + '</textarea></label>' +
            '<p class="checklist-disclaimer">Статусы фиксируют фактическое наблюдение сотрудника и сами по себе не являются юридическим заключением о соответствии. Перед использованием сверяйте источник и применимость к вашей организации.</p>' +
            '</div>' +
            '<div class="checklist-actions no-print">' +
            (readOnly ? '<button class="btn btn-primary" type="button" onclick="window.print()">Печать проверки</button><button class="btn btn-secondary" type="button" onclick="ChecklistEditor.startNew()">Новая проверка</button>' : '<button class="btn btn-success" type="button" id="save-checklist-btn">Сохранить проверку</button><button class="btn btn-secondary" type="button" onclick="window.print()">Предварительная печать</button>') +
            '</div>';
        if (!readOnly) document.getElementById('save-checklist-btn').addEventListener('click', () => this.save());
    },

    async save() {
        const responsible = document.getElementById('checklist-responsible').value.trim();
        const performedAt = document.getElementById('checklist-datetime').value;
        if (responsible.length < 2 || !performedAt) {
            alert('Укажите ответственного и дату проверки.');
            return;
        }
        const items = [...document.querySelectorAll('.checklist-item')].map((row) => ({
            item_key: row.dataset.itemKey,
            status: row.querySelector('.item-status').value,
            actual: row.querySelector('.item-actual').value.trim(),
            note: row.querySelector('.item-note').value.trim()
        }));
        const unchecked = items.filter((item) => item.status === 'unchecked').length;
        if (unchecked) {
            alert('Перед сохранением отметьте результат по каждому пункту. Не проверенные пункты: ' + unchecked + '.');
            document.querySelector('.checklist-item .item-status[value="unchecked"]')?.focus();
            return;
        }
        const payload = {
            template_key: this.activeTemplate.key,
            responsible,
            performed_at: performedAt,
            overall_note: document.getElementById('checklist-overall-note').value.trim(),
            items
        };
        const button = document.getElementById('save-checklist-btn');
        button.disabled = true;
        try {
            const saved = await API.createChecklistInspection(payload);
            this.inspections.unshift(saved);
            this.renderHistory();
            this.activeInspection = saved;
            this.renderForm(saved);
        } catch (error) {
            alert('Не удалось сохранить проверку. Проверьте подключение и повторите попытку.');
            button.disabled = false;
        }
    }
};

function escapeChecklistHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, function(character) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character];
    });
}

document.addEventListener('DOMContentLoaded', function() {
    ChecklistEditor.init();
});
