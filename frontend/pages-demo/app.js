const categoryNames = {
    emergency: 'Неотложные состояния',
    'infection-control': 'Инфекционная безопасность',
    sterilization: 'Очистка и стерилизация',
    sanitary: 'Санитарный режим',
    'medical-waste': 'Медицинские отходы',
    equipment: 'Оборудование и укладки',
    'clinical-safety': 'Безопасность медицинской деятельности',
    'clinic-organization': 'Организация клиники'
};
const fields = [
    ['scope', '1. Область применения'],
    ['normative_refs', '2. Нормативные ссылки'],
    ['terms', '3. Термины и определения'],
    ['responsibilities', '4. Ответственность'],
    ['procedure', '5. Процедура'],
    ['quality_control', '6. Контроль качества'],
    ['documentation', '7. Документирование']
];

const listElement = document.getElementById('sops-list');
const detailElement = document.getElementById('sop-detail');
const searchElement = document.getElementById('sop-search');
const categoryElement = document.getElementById('category-filter');
const resultCountElement = document.getElementById('result-count');
let sops = [];
let selectedId = null;

function addText(parent, tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    parent.appendChild(element);
    return element;
}

function renderList() {
    const query = searchElement.value.trim().toLocaleLowerCase('ru');
    const category = categoryElement.value;
    const filtered = sops.filter((sop) => {
        return (!category || sop.category === category) && sop.title.toLocaleLowerCase('ru').includes(query);
    });
    resultCountElement.textContent = 'Найдено: ' + filtered.length;
    listElement.replaceChildren();
    filtered.forEach((sop) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'sop-link';
        button.setAttribute('aria-current', String(sop.id === selectedId));
        addText(button, 'span', 'sop-link-title', 'СОП №' + sop.number + '. ' + sop.title);
        addText(button, 'span', 'sop-link-meta', categoryNames[sop.category] || sop.category);
        button.addEventListener('click', () => renderDetail(sop));
        listElement.appendChild(button);
    });
}

function renderDetail(sop) {
    selectedId = sop.id;
    detailElement.replaceChildren();

    const header = document.createElement('div');
    header.className = 'detail-head';
    const titleBlock = document.createElement('div');
    addText(titleBlock, 'span', 'detail-number', 'ПРОЕКТ СОП №' + sop.number);
    addText(titleBlock, 'h2', '', sop.title);
    addText(titleBlock, 'p', 'category-label', categoryNames[sop.category] || sop.category);
    header.appendChild(titleBlock);

    const actions = document.createElement('div');
    actions.className = 'detail-actions';
    addText(actions, 'span', 'draft-stamp', 'ЧЕРНОВИК');
    const printButton = addText(actions, 'button', 'print-button', 'Печать');
    printButton.type = 'button';
    printButton.addEventListener('click', () => window.print());
    header.appendChild(actions);
    detailElement.appendChild(header);

    addText(detailElement, 'p', 'draft-warning', 'Демонстрационный проект. Не утверждён и не проверен для практического применения. Перед использованием проверьте актуальность требований по официальным источникам и адаптируйте документ к фактическим условиям клиники.');
    fields.forEach(([key, label]) => {
        const section = document.createElement('section');
        section.className = 'sop-section';
        addText(section, 'h3', '', label);
        addText(section, 'p', '', sop[key] || 'Не заполнено в примере.');
        detailElement.appendChild(section);
    });
    renderList();
}

function populateCategories() {
    Object.entries(categoryNames).forEach(([key, label]) => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = label;
        categoryElement.appendChild(option);
    });
}

searchElement.addEventListener('input', renderList);
categoryElement.addEventListener('change', renderList);

fetch('./sops.json')
    .then((response) => {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
    })
    .then((data) => {
        sops = data;
        populateCategories();
        renderList();
    })
    .catch(() => {
        resultCountElement.textContent = 'Каталог временно недоступен';
        addText(listElement, 'p', '', 'Не удалось загрузить примеры СОПов. Обновите страницу позже.');
    });