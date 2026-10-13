# ИНСТРУКЦИЯ ПО ЗАПУСКУ DENTAL AI PLATFORM

ШАГ 0. Требования
    Python 3.11 или 3.12 (Python 3.13 и новее не поддерживаются).
    Скачать: https://www.python.org/downloads/ , при установке отметить "Add python.exe to PATH".
    Проверка: py -3.12 --version

ШАГ 1. Быстрый запуск
    Запустить start.bat из корня проекта. Скрипт сам:
    - найдёт Python 3.11/3.12 и создаст backend\venv;
    - установит зависимости из backend\requirements.txt;
    - создаст backend\.env из .env.example (если его нет);
    - создаст каталог из 88 черновиков СОП;
    - запустит сервер.

ШАГ 1a. Ручной запуск (если start.bat не подходит)
    cd backend
    py -3.12 -m venv venv
    venv\Scripts\activate
    python -m pip install -r requirements.txt
    python seed_sops.py
    python run.py
    Swagger: http://127.0.0.1:9090/docs

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
