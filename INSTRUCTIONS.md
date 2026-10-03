# ИНСТРУКЦИЯ ПО ЗАПУСКУ DENTAL AI PLATFORM

ШАГ 1. Зависимости backend
    cd backend
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

ШАГ 2. Создание каталога из 88 черновиков СОП
    python seed_sops.py

ШАГ 3. Запуск (порт 9090)
    python run.py
    Swagger: http://localhost:9090/docs

ШАГ 4. Frontend
    Открыть http://127.0.0.1:9090/ в браузере.
    Frontend и API обслуживаются одним сервером на порту 9090.
    Для совместного запуска можно использовать start.bat в корне проекта.
    Отдельный http.server и открытие HTML через file:// не нужны.

ШАГ 5. Ключи ИИ
    Вписать в backend\.env : GIGACHAT_CLIENT_ID, GIGACHAT_CLIENT_SECRET, YANDEX_IAM_TOKEN, YANDEX_FOLDER_ID

СОПы создаются как проекты, а не как подтверждение нормативного соответствия.
Перед утверждением проверьте каждый источник и пункт по официальной публикации,
сверьте фактические штат, помещения, оснащение, лицензию и договоры клиники.

ВЕРСИЯ 1.0.0, сентябрь 2026
