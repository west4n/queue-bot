# Pogran Bot - Telegram бот для отслеживания очереди на границе

## 📋 Описание проекта

**Pogran Bot** — это Telegram-бот на Python, разработанный для отслеживания очереди автомобилей на белорусских пограничных пунктах пропуска. Бот позволяет пользователям:

- Отслеживать очередь на границе в реальном времени
- Добавлять до 3 номеров автомобилей для мониторинга
- Получать уведомления о продвижении очереди (по времени или количеству машин)
- Просматривать информацию о первом автомобиле в очереди
- Просматривать камеры с пограничных пунктов
- Администраторам: создавать массовые рассылки пользователям
- Администраторам: просматривать статистику платежей (полученные звезды, возвраты, конвертация в доллары)

## 🏗️ Архитектура проекта

Проект построен на **aiogram 3.6.0** (асинхронный фреймворк для Telegram Bot API) и использует следующую архитектуру:

```
pogran-bot/
├── main.py                 # Точка входа, инициализация бота и диспетчера
├── config_data/            # Конфигурация и настройки
│   └── config.py          # Загрузка переменных окружения и конфигурация
├── database/              # Работа с базой данных
│   ├── models.py          # SQLAlchemy модели (User, Payment)
│   └── requests.py        # Функции для работы с БД (CRUD операции)
├── handlers/              # Обработчики сообщений и callback'ов
│   ├── user.py           # Обработка команды /start и главного меню
│   ├── admin.py          # Административные функции (/admin)
│   ├── my_cars.py        # Управление списком автомобилей пользователя
│   ├── payment.py        # Обработка успешных платежей через Telegram Stars
│   └── other.py          # Дополнительные команды (/reset)
├── states/                # FSM состояния для многошаговых диалогов
│   ├── add_car.py        # Состояние добавления автомобиля
│   ├── delete_car.py     # Состояние удаления автомобиля
│   ├── queue_state.py    # Состояние просмотра очереди
│   ├── queue_first_auto.py  # Состояние просмотра первого авто
│   ├── show_camera.py    # Состояние просмотра камер
│   └── state_mail.py     # Состояние создания рассылки (админ)
├── services/             # Бизнес-логика и сервисы
│   ├── border_api.py     # Асинхронные функции для работы с API границы
│   ├── find_my_car.py    # Поиск автомобиля по номеру в API границы
│   ├── track_car_minutes.py  # Отслеживание по интервалу времени
│   └── track_car_queue.py     # Отслеживание по количеству машин
├── keyboards/            # Построение клавиатур
│   ├── kb_builder.py    # Утилиты для создания inline-клавиатур
│   └── start_menu.py    # Настройка команд меню бота
├── lexicon/             # Текстовые константы и словари
│   └── lexicon.py       # Все текстовые сообщения и callback_data
├── filters/             # Кастомные фильтры
│   └── is_admin.py      # Фильтр проверки администратора
├── utils/               # Вспомогательные утилиты
│   └── sender.py        # Функции для массовой рассылки
└── migrations/          # Миграции базы данных (Alembic)
```

## 🔧 Технологический стек

- **Python 3.11+** (предположительно, судя по синтаксису)
- **aiogram 3.6.0** — асинхронный фреймворк для Telegram Bot API
- **SQLAlchemy 2.0.30** — ORM для работы с базой данных
- **asyncpg 0.29.0** — асинхронный драйвер PostgreSQL
- **Alembic 1.13.1** — миграции базы данных
- **PostgreSQL** — база данных
- **aiohttp 3.9.5** — асинхронные HTTP-запросы к API границы
- **environs 11.0.0** — управление переменными окружения

## 📦 Установка и настройка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd pogran-bot
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка базы данных (Docker Compose)

Проект включает `docker-compose.yml` с PostgreSQL 17 для локальной разработки.

**Запуск PostgreSQL через Docker Compose:**

```bash
# Запустить PostgreSQL
docker-compose up -d postgres

# Проверить статус
docker-compose ps

# Остановить PostgreSQL
docker-compose down
```

База данных будет доступна по адресу: `postgresql+asyncpg://postgres:postgres@localhost:5432/pogran_bot`

**Применение миграций:**

```bash
alembic upgrade head
```

### 4. Настройка переменных окружения

Создайте файл `.env` в корне проекта на основе `.env.example`:

```bash
cp .env.example .env
```

Отредактируйте `.env` со следующим содержимым:

```env
BOT_TOKEN=your_telegram_bot_token
BASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pogran_bot
BORDERS={"53d94097-2b34-11ec-8467-ac1f6bf889c0":"Бенякони","b60677d4-8a00-4f93-a781-e129e1692a03":"Каменный лог","b7b368c7-d00c-11e7-a46c-001517da0c91":"Котловка","ffe81c11-00d6-11e8-a967-b0dd44bde851":"Григоровщина","a9173a85-3fc0-424c-84f0-defa632481e4":"Брест","98b5be92-d3a5-4ba2-9106-76eb4eb3df49":"Козловичи","b797d4d-706a-440f-a1a4-826c191e1e36":"Брузги","7e46a2d1-ab2f-11ec-bafb-ac1f6bf889c1":"Берестовица"}

# Настройки для платных звонков через Telegram Stars
CALL_STAR_PRICE=100
CALL_MODE=test
CALL_HANGUP_DELAY=5

# Настройки Twilio (требуются только для CALL_MODE=prod)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_PHONE=+1234567890
```

Где:

- `BOT_TOKEN` — токен вашего Telegram бота (получить у @BotFather)
- `BASE_URL` — строка подключения к PostgreSQL базе данных
  - Для Docker Compose: `postgresql+asyncpg://postgres:postgres@localhost:5432/pogran_bot`
  - Для продакшн: `postgresql+asyncpg://user:password@host:5432/dbname`
- `BORDERS` — JSON-строка с маппингом ID границ на их названия (опционально, если не указано, используются значения по умолчанию)
- `CALL_STAR_PRICE` — стоимость телефонного звонка в Telegram Stars (по умолчанию: 100)
- `CALL_MODE` — режим работы звонков: `test` (имитация) или `prod` (реальные звонки через Twilio, по умолчанию: `test`)
- `CALL_HANGUP_DELAY` — время в секундах, в течение которого звонок будет звонить перед автоматическим завершением (по умолчанию: 5). Используется для предотвращения ответа на звонок и экономии средств.
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_PHONE` — учетные данные Twilio (требуются только при `CALL_MODE=prod`)

**Примечание:** Переменная `BORDERS` опциональна. Если она не указана в `.env`, будут использоваться значения по умолчанию, включающие все доступные границы. Для добавления новых границ или изменения существующих отредактируйте эту переменную в формате JSON.

### 5. Настройка базы данных (без Docker)

Если вы не используете Docker Compose, настройте PostgreSQL вручную и примените миграции:

```bash
alembic upgrade head
```

Или база данных будет создана автоматически при первом запуске через `async_main()` в `database/models.py`.

### 6. Настройка администраторов

В файле `config_data/config.py` указаны ID администраторов:

```python
ADMIN_IDS = [344786301, 538297748]
```

Замените на свои Telegram ID (можно узнать у @userinfobot).

### 7. Настройка путей к камерам

В файле `states/show_camera.py` указаны пути к скриншотам камер:

- `~/screen-script/screens/kam_log_camera_1.jpg`
- `~/screen-script/screens/kam_log_camera_2.jpg`
- `~/screen-script/screens/brest_camera.jpg`
- `~/screen-script/screens/grigorovchina.jpg`

Убедитесь, что эти файлы существуют или измените пути под вашу систему.

## 🚀 Запуск бота

```bash
python main.py
```

## 🚀 Автоматический деплой на Ubuntu сервер

Проект поддерживает автоматический деплой на Ubuntu сервер через GitHub Actions с использованием self-hosted runner.

### Предварительные требования на сервере

1. **Установка Docker и Docker Compose:**

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **Установка Python 3.11+:**

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip -y
```

3. **Установка Git:**

```bash
sudo apt install git -y
```

4. **Создание пользователя `pogran`:**

```bash
sudo useradd -m -s /bin/bash pogran
sudo usermod -aG docker pogran
```

5. **Создание директории проекта:**

```bash
sudo mkdir -p /opt/pogran-bot
sudo chown pogran:pogran /opt/pogran-bot
```

6. **Клонирование репозитория:**

```bash
sudo -u pogran git clone <repository-url> /opt/pogran-bot
cd /opt/pogran-bot
sudo -u pogran git checkout main
```

### Настройка Self-Hosted GitHub Runner

1. **Установка GitHub Runner:**

```bash
# Переходим в директорию пользователя
cd /home/pogran

# Скачиваем последнюю версию runner
sudo -u pogran mkdir actions-runner && cd actions-runner
sudo -u pogran curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
sudo -u pogran tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz
```

2. **Настройка runner:**

```bash
# Получите токен настройки в GitHub:
# Settings → Actions → Runners → New self-hosted runner
sudo -u pogran ./config.sh --url https://github.com/YOUR_USERNAME/YOUR_REPO --token YOUR_TOKEN --labels self-hosted
```

3. **Установка runner как сервиса:**

```bash
sudo ./svc.sh install pogran
sudo ./svc.sh start
```

4. **Настройка прав для runner:**

```bash
# Добавляем пользователя runner в группу docker (если еще не добавлен)
sudo usermod -aG docker $USER

# Настраиваем sudo без пароля для команды systemctl (опционально, для удобства)
echo "pogran ALL=(ALL) NOPASSWD: /bin/systemctl" | sudo tee /etc/sudoers.d/pogran
```

### Настройка переменных окружения

1. **Создание файла `.env`:**

```bash
cd /opt/pogran-bot
sudo -u pogran cp .env.example .env
sudo -u pogran nano .env
```

2. **Заполните переменные в `.env`:**

- `BOT_TOKEN` — токен Telegram бота
- `BASE_URL` — строка подключения к PostgreSQL (для Docker Compose используйте: `postgresql+asyncpg://postgres:postgres@localhost:5432/pogran_bot`)
- Остальные переменные при необходимости

### Установка Systemd Service

1. **Копирование service файла:**

```bash
sudo cp /opt/pogran-bot/deploy/pogran-bot.service /etc/systemd/system/
```

2. **Перезагрузка systemd и включение автозапуска:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable pogran-bot.service
```

**Примечание:** Не запускайте сервис сразу — он будет запущен после первого деплоя.

### Первый деплой и восстановление базы данных

1. **Первый автоматический деплой:**

   - Сделайте push в ветку `main` — GitHub Actions автоматически выполнит деплой
   - Или запустите workflow вручную через GitHub UI

2. **Восстановление backup базы данных:**

```bash
cd /opt/pogran-bot
sudo -u pogran bash deploy/first-deploy.sh
```

Скрипт `first-deploy.sh` выполнит:

- Восстановление базы данных из `docs/pogran_bot_backup_20251116_190123.dump`
- Применение всех миграций Alembic до последней версии
- Запуск сервиса бота

3. **Проверка работы бота:**

```bash
# Проверка статуса сервиса
sudo systemctl status pogran-bot.service

# Просмотр логов
sudo journalctl -u pogran-bot.service -f
```

### Последующие деплои

После настройки все последующие деплои выполняются автоматически при push в ветку `main`. GitHub Actions:

1. Обновит код из репозитория
2. Установит зависимости
3. Запустит Docker Compose для PostgreSQL
4. Применит миграции Alembic
5. Перезапустит сервис бота

### Управление сервисом

```bash
# Запуск
sudo systemctl start pogran-bot.service

# Остановка
sudo systemctl stop pogran-bot.service

# Перезапуск
sudo systemctl restart pogran-bot.service

# Статус
sudo systemctl status pogran-bot.service

# Логи
sudo journalctl -u pogran-bot.service -f
```

### Устранение неполадок

1. **Проверка логов GitHub Actions:**

   - Перейдите в раздел Actions вашего репозитория
   - Откройте последний запуск workflow

2. **Проверка логов сервиса:**

```bash
sudo journalctl -u pogran-bot.service -n 100
```

3. **Проверка Docker Compose:**

```bash
cd /opt/pogran-bot
docker-compose ps
docker-compose logs postgres
```

4. **Проверка подключения к БД:**

```bash
docker-compose exec postgres psql -U postgres -d pogran_bot -c "SELECT COUNT(*) FROM users;"
```

5. **Ручной запуск деплоя:**

```bash
cd /opt/pogran-bot
sudo -u pogran bash deploy/deploy.sh
```

### Восстановление backup базы данных поверх существующих данных

Если у вас уже есть данные в Docker PostgreSQL и вы хотите перезалить новый бэкап:

1. **Использование скрипта восстановления (рекомендуется):**

```bash
cd /opt/pogran-bot
sudo -u pogran bash deploy/restore-backup.sh docs/pogran_bot_backup_20251116_190123.dump
```

Скрипт `restore-backup.sh` выполнит:

- Остановку сервиса бота
- Удаление существующей базы данных
- Создание новой пустой базы данных
- Восстановление из указанного backup файла
- Применение всех миграций Alembic до последней версии
- Запуск сервиса бота

**Важно:** Скрипт запросит подтверждение перед удалением существующих данных.

2. **Ручное восстановление (если нужно больше контроля):**

```bash
# Остановка бота
sudo systemctl stop pogran-bot.service

# Убедитесь, что PostgreSQL запущен
cd /opt/pogran-bot
docker-compose up -d postgres

# Удаление существующей БД и создание новой
docker-compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS pogran_bot;"
docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE pogran_bot;"

# Восстановление из backup
docker-compose exec -T postgres pg_restore -U postgres -d pogran_bot --clean --if-exists < docs/pogran_bot_backup_20251116_190123.dump

# Применение миграций
source venv/bin/activate
alembic upgrade head

# Запуск бота
sudo systemctl start pogran-bot.service
```

3. **Полное удаление данных Docker (если нужно начать с нуля):**

```bash
# Остановка всех контейнеров
cd /opt/pogran-bot
docker-compose down

# Удаление volume с данными PostgreSQL (ВНИМАНИЕ: все данные будут удалены!)
docker volume rm pogran-bot_postgres_data

# Запуск PostgreSQL заново
docker-compose up -d postgres

# Далее используйте скрипт восстановления или ручное восстановление
```

## 🔄 Миграция базы данных

Если вы обновляете существующую базу данных с продакшн-сервера, см. подробное руководство:

📖 **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** — Руководство по миграции БД с бэкапом и восстановлением состояния

**Быстрый старт для миграции:**

1. Создайте бэкап: `./backup_db.sh [HOST] [USER] [DATABASE]`
2. Восстановите на локальной машине (через Docker Compose)
3. Примените миграции: `alembic upgrade head`
4. Проверьте данные
5. Обновите продакшн-сервер

## 📚 Детальное описание компонентов

### main.py

**Основной файл запуска бота.** Содержит:

- Инициализацию бота и диспетчера (`Bot`, `Dispatcher`)
- Глобальный словарь `tracking_tasks` для хранения активных задач отслеживания
- Регистрацию всех роутеров из модулей `handlers` и `states`
- Обработчики callback'ов для отслеживания:
  - `process_callback_track_minutes` — запуск отслеживания по времени (5/10/15 минут)
  - `process_callback_track_cars` — запуск отслеживания по количеству машин (15/30)
  - `process_callback_remove_alert` — остановка отслеживания

**Важно:** Задачи отслеживания создаются через `asyncio.create_task()` и хранятся в `tracking_tasks[user.tg_id]`. При остановке задачи она удаляется из словаря.

### database/models.py

**Модели базы данных.** Определяет:

- `Base` — базовый класс для всех моделей (наследуется от `AsyncAttrs`, `DeclarativeBase`)
- `User` — модель пользователя со следующими полями:
  - `id` — первичный ключ (BigInteger)
  - `tg_id` — уникальный Telegram ID пользователя
  - `name` — имя пользователя
  - `car_numbers` — массив номеров автомобилей (ARRAY, максимум 3)
  - `track_number` — активный номер для отслеживания
  - `type_car` — тип автомобиля (не используется активно)
  - `border` — граница (не используется активно)
  - `is_active` — флаг активности пользователя
- `Payment` — модель платежей со следующими полями:
  - `id` — первичный ключ (BigInteger, автоинкремент)
  - `tg_id` — Telegram ID пользователя
  - `payment_charge_id` — ID платежа от Telegram
  - `amount` — количество звезд (Integer)
  - `payment_type` — тип операции: "payment" (платеж) или "refund" (возврат)
  - `created_at` — время создания записи (DateTime)

**Подключение к БД:** Использует `create_async_engine` с URL из конфига и создает `async_sessionmaker` для работы с сессиями.

### database/requests.py

**CRUD операции для работы с пользователями и платежами.** Содержит функции:

**Работа с пользователями:**

- `set_user(tg_id, name)` — создание нового пользователя
- `get_user(tg_id)` — получение пользователя по Telegram ID
- `get_total_users()` — подсчет общего количества пользователей
- `set_car_number(tg_id, car_number)` — добавление номера автомобиля в массив
- `set_active_car_number(tg_id, car_number)` — установка активного номера для отслеживания
- `delete_car_number(tg_id, car_number)` — удаление номера из массива
- `get_users()` — получение списка всех Telegram ID пользователей

**Работа с платежами:**

- `save_payment(tg_id, payment_charge_id, amount)` — сохранение успешного платежа
- `save_refund(tg_id, payment_charge_id, amount)` — сохранение возврата средств
- `get_payment_by_charge_id(payment_charge_id)` — получение платежа по ID для возвратов
- `get_last_test_payment(tg_id)` — получение последнего тестового платежа для пользователя
- `get_payment_statistics()` — получение статистики платежей:
  - Общее количество полученных звезд
  - Общее количество возвращенных звезд
  - Чистая сумма (полученные - возвращенные)
  - Конвертация в доллары (1 звезда = $0.013)

**Важно:**

- Все номера сохраняются в верхнем регистре через `.upper()`.
- В тестовом режиме (`CALL_MODE=test`) платежи также сохраняются в БД с фиктивным `payment_charge_id` (формат: `TEST_MODE_{tg_id}_{timestamp}`) и суммой из `CALL_STAR_PRICE`. Это позволяет тестировать статистику платежей без реальных транзакций через Telegram Stars.

### handlers/user.py

**Обработчик команды /start и главного меню.**

- `process_start_command` — обрабатывает `/start` и callback `main_menu`
- Регистрирует пользователя в БД при первом запуске
- Показывает количество добавленных машин (до 3)
- Отображает главное меню с кнопками из `lexicon`

### handlers/admin.py

**Административные функции.**

- `process_command_admin_start` — команда `/admin` (доступна только администраторам)
- Показывает статистику: количество пользователей в базе
- Предоставляет возможность создать рассылку через `process_callback_text_admin_mail`
- `process_callback_payment_statistics` — отображение статистики платежей:
  - Получено звезд (сумма всех успешных платежей)
  - Возвращено звезд (сумма всех возвратов)
  - Чистая сумма (полученные - возвращенные)
  - Конвертация в доллары с курсом 1 звезда = $0.013

**Фильтр доступа:** Использует кастомный фильтр `IsAdmin(ADMIN_IDS)`.

### handlers/payment.py

**Обработка платежей через Telegram Stars.**

- `process_successful_payment` — обработка успешного платежа:
  - Проверяет, что платеж в валюте XTR (Telegram Stars)
  - Парсит payload для определения типа покупки
  - Сохраняет платеж в БД через `save_payment()`
  - Переходит к запросу номера телефона для звонка

**Важно:** Платежи автоматически сохраняются в таблицу `payments` для последующей статистики.

### handlers/my_cars.py

**Управление списком автомобилей пользователя.**

- `process_callback_my_cars` — отображение списка машин пользователя
- `process_callback_track_car` — выбор машины для отслеживания
  - Ищет машину через `find_my_car(car_number)`
  - Показывает информацию: ЗО, номер в очереди, дата регистрации
  - Предлагает варианты отслеживания (по времени или количеству машин)
  - Устанавливает активный номер через `set_active_car_number`

**Ограничения:** Максимум 3 машины на пользователя.

### services/find_my_car.py

**Поиск автомобиля в API границы.**

Функция `find_my_car(car_number)`:

- Перебирает все границы из `LEXICON_BUTTONS_BORDERS`
- Делает запрос к `https://belarusborder.by/info/monitoring-new?token=test&checkpointId={borderId}`
- Ищет номер в очередях: `truckLiveQueue`, `carLiveQueue`, `busLiveQueue`
- Возвращает словарь с информацией о машине и границе или `None`

**Важно:** Использует синхронный `requests.get()`, что может блокировать event loop. Рекомендуется переписать на `aiohttp`.

### services/track_car_minutes.py

**Отслеживание автомобиля по интервалу времени.**

Функция `track_car_minutes(bot, tg_id, car_number, interval)`:

- Запускается как асинхронная задача
- Отправляет начальное сообщение об успешном включении уведомлений
- В бесконечном цикле:
  - Проверяет статус машины каждые `interval` минут
  - Если `status == 2` (в очереди) — отправляет обновление с номером в очереди
  - Если `status == 1` (вызвана) — отправляет финальное сообщение и завершает цикл
  - Если машина не найдена (`None`) — также завершает цикл
- Использует `asyncio.sleep(interval * 60)` для паузы

**Статусы машины:**

- `2` — в очереди (есть `order_id`)
- `3` — вызвана на пропускной пункт (`order_id: None`)
- `9` — обработана (`order_id: None`)

### services/track_car_queue.py

**Отслеживание автомобиля по количеству машин в очереди.**

Функция `track_car_queue(bot, tg_id, car_number, queue_size, poll_interval)`:

- Запоминает начальный `order_id` при первом нахождении машины
- Отправляет уведомление когда очередь продвинулась на `queue_size` машин
- Отправляет предупреждение когда очередь <= 2
- Завершается при статусе `1` или если машина не найдена
- Проверяет каждые `poll_interval` минут (по умолчанию 4 минуты)

**Логика:** `initial_order_id - car_info["car"]["order_id"] >= queue_size`

### states/add_car.py

**FSM состояние для добавления автомобиля.**

- `AddCarState.car_number` — состояние ввода номера
- `process_callback_add_car` — инициирует процесс добавления
- `process_state_car_number` — обрабатывает введенный номер
  - Валидация через regex: `^[a-zA-Z0-9]{6,8}$`
  - Сохранение через `set_car_number`

### states/queue_state.py

**FSM состояние для просмотра очереди на границе.**

Многошаговый процесс:

1. Выбор границы (`QueueState.border`)
2. Выбор типа транспорта (`QueueState.car_type`)
3. Получение данных из API и отображение количества машин в очереди

**Типы транспорта:**

- `car_type` → `carLiveQueue` (легковые)
- `truck_type` → `truckLiveQueue` (грузовые)
- `bus_type` → `busLiveQueue` (автобусы)

### states/queue_first_auto.py

**FSM состояние для просмотра информации о первом автомобиле.**

Аналогично `queue_state.py`, но дополнительно показывает:

- Дата регистрации первого автомобиля
- Статистику за последний час и последние 24 часа

Использует два API-эндпоинта:

- `/monitoring-new` — текущая очередь
- `/monitoring/statistics` — статистика

### states/show_camera.py

**FSM состояние для просмотра камер.**

- `ShowCameraState.border` — выбор границы с камерой
- Отправляет фото из локальной файловой системы
- Для Каменного лога отправляет медиагруппу (2 фото)

**Пути к файлам:** Использует `os.path.expanduser("~/screen-script/screens/...")`

### states/state_mail.py

**FSM состояние для создания административной рассылки.**

Многошаговый процесс:

1. `CreateMessage.theme_text` — ввод темы рассылки
2. `CreateMessage.message_text` — ввод текста рассылки
3. `CreateMessage.confirm_sender` — подтверждение и запуск

Использует `utils/sender.py`:

- `send_preview` — отправка превью сообщения
- `start_sender` — массовая рассылка всем пользователям

**Особенности рассылки:**

- Обрабатывает `TelegramRetryAfter` (ограничение rate limit)
- Задержка 0.05 секунды между сообщениями
- Показывает статистику: отправлено/всего за время

### keyboards/kb_builder.py

**Утилиты для построения inline-клавиатур.**

Функции:

- `inline_builder_text` — универсальный построитель кнопок из списков
- `inline_build_car_buttons` — клавиатура со списком машин и кнопкой "Добавить"
- `inline_build_car_buttons_without_add` — клавиатура без кнопки "Добавить" (когда 3 машины)
- `inline_build_group` — кнопка-ссылка на группу
- `inline_build_group_with_menu` — кнопка группы + "Главное меню"
- `inline_build_group_with_alert` — кнопка группы + "Отменить уведомления"

### lexicon/lexicon.py

**Централизованное хранение всех текстов и callback_data.**

Содержит:

- `LEXICON_TEXT_START` — приветственное сообщение
- `LEXICON_COMMANDS` — команды бота для меню
- `LEXICON_BUTTONS_*` — словари с текстами кнопок и их callback_data
- `LEXICON_BUTTONS_BORDERS` — маппинг ID границ на их названия
- Списки ключей и значений для удобного использования в клавиатурах

**Границы:**

- Бенякони
- Каменный лог
- Котловка
- Григоровщина
- Брест
- Козловичи
- Брузги
- Берестовица

**Примечание:** `LEXICON_BUTTONS_BORDERS` теперь загружается из конфигурации (`config_data/config.py`), которая читает данные из переменной окружения `BORDERS` в файле `.env`. Это позволяет легко добавлять или изменять границы без изменения кода.

### utils/sender.py

**Утилиты для массовой рассылки.**

- `send_preview` — отправка превью сообщения администратору
- `send_mail` — отправка одного сообщения с обработкой rate limit
- `start_sender` — цикл рассылки всем пользователям

**Обработка ошибок:** Рекурсивно обрабатывает `TelegramRetryAfter`, ожидая `retry_after` секунд.

### filters/is_admin.py

**Кастомный фильтр для проверки администратора.**

Класс `IsAdmin`:

- Принимает один ID или список ID
- Проверяет `message.from_user.id` на соответствие

## 🔄 Потоки данных

### Добавление автомобиля

```
Пользователь → /start → "Мои машины" → "Добавить машину"
→ Ввод номера → Валидация → Сохранение в БД → Подтверждение
```

### Отслеживание по времени

```
Пользователь → Выбор машины → "5/10/15 минут"
→ Создание задачи track_car_minutes → Цикл проверки каждые N минут
→ Уведомления при изменении → Завершение при статусе 1 или None
```

### Отслеживание по количеству машин

```
Пользователь → Выбор машины → "15/30 машин"
→ Создание задачи track_car_queue → Запоминание начального order_id
→ Проверка каждые 4 минуты → Уведомление при продвижении на N машин
→ Завершение при статусе 1 или None
```

## 🐛 Известные проблемы и рекомендации

1. **Управление задачами:** Задачи отслеживания хранятся в словаре `tracking_tasks` в памяти. При перезапуске бота все активные отслеживания теряются. Рекомендуется сохранять состояние в БД.

2. **Обработка ошибок API:** Базовая обработка ошибок добавлена, но рекомендуется добавить retry логику для повышения надежности.

3. **Валидация номеров:** Regex `^[a-zA-Z0-9]{6,8}$` может не соответствовать всем форматам белорусских номеров. Рекомендуется уточнить формат.

4. **Пути к камерам:** Жестко закодированные пути в `states/show_camera.py`. Рекомендуется вынести в конфигурацию.

5. **Лимит машин:** Логика ограничения 3 машин реализована только в UI, но не в БД (нет constraint). Рекомендуется добавить проверку перед сохранением.

## 📝 API границы

Бот использует публичное API белорусской границы:

- **Текущая очередь:** `https://belarusborder.by/info/monitoring-new?token=test&checkpointId={borderId}`
- **Статистика:** `https://belarusborder.by/info/monitoring/statistics?token=test&checkpointId={borderId}`

**Формат ответа:**

```json
{
  "carLiveQueue": [...],
  "truckLiveQueue": [...],
  "busLiveQueue": [...],
  ...
}
```

**Структура объекта машины:**

```json
{
	"regnum": "1234AX7",
	"order_id": 15,
	"status": 2,
	"registration_date": "2024-01-01 12:00:00",
	"type_queue": "car",
	"changed_date": "2024-01-01 12:30:00"
}
```

**Статусы машины:**

- `status: 2` — машина в очереди (есть `order_id`)
- `status: 3` — машина вызвана на пропускной пункт (`order_id: null`)
- `status: 9` — машина обработана (`order_id: null`)

**Важно:** При статусе 3 или 9 поле `order_id` будет `null`, так как машина уже вызвана или обработана.

## 🔐 Безопасность

- Токен бота хранится в переменных окружения (`.env`)
- Административные функции защищены фильтром `IsAdmin`
- Номера автомобилей сохраняются в верхнем регистре для единообразия
- Нет валидации входных данных от API (может быть уязвимость при изменении формата)

## 📈 Возможные улучшения

1. Добавить логирование всех операций
2. Сохранять состояние отслеживания в БД для восстановления после перезапуска
3. Добавить кэширование результатов API-запросов
4. Реализовать очередь задач для рассылки через Redis/RabbitMQ
5. Добавить метрики и мониторинг (Prometheus, Grafana)
6. Добавить unit-тесты и интеграционные тесты
7. Реализовать систему уведомлений об ошибках (Sentry)
8. Добавить возможность настройки интервалов отслеживания пользователем
9. Реализовать историю отслеживаний для аналитики
10. Добавить retry логику для HTTP-запросов к API границы

## 📞 Контакты и поддержка

Для вопросов и предложений обращайтесь к разработчику проекта.

---

## 📝 История изменений

### Версия 1.1.0 (2024-11-12)

**Миграция на асинхронные HTTP-запросы:**

- ✅ Переписаны все HTTP-запросы с `requests` на `aiohttp` для предотвращения блокировки event loop
- ✅ Создан новый модуль `services/border_api.py` с асинхронными функциями для работы с API
- ✅ Улучшена производительность: параллельные запросы ко всем границам в `find_my_car()`
- ✅ Добавлена обработка ошибок (timeout, connection errors, JSON parsing)
- ✅ Удалена зависимость `requests` из `requirements.txt`

**Улучшена обработка статусов машин:**

- ✅ Добавлена корректная обработка статуса 3 (вызвана в ПП)
- ✅ Улучшена обработка случаев, когда `order_id` может быть `None`
- ✅ Обновлены сообщения для пользователей в зависимости от статуса машины
- ✅ Исправлена обработка статусов в `track_car_minutes.py` и `track_car_queue.py`

**Версия:** 1.1.0  
**Последнее обновление:** 2024-11-12

### Версия 1.2.0 (2024-11-18)

**Добавлена статистика платежей для администраторов:**

- ✅ Создана модель `Payment` для хранения платежей и возвратов
- ✅ Добавлена миграция для таблицы `payments` с индексами
- ✅ Реализовано автоматическое сохранение успешных платежей при оплате через Telegram Stars
- ✅ Реализовано автоматическое сохранение возвратов при отмене покупки
- ✅ Добавлена функция `get_payment_statistics()` для подсчёта статистики:
  - Общее количество полученных звезд
  - Общее количество возвращенных звезд
  - Чистая сумма (полученные - возвращенные)
  - Автоматическая конвертация в доллары (1 звезда = $0.013)
- ✅ Добавлена кнопка "Статистика платежей" в админ-панель (`/admin`)
- ✅ Статистика отображается в удобном формате с эмодзи и форматированием
- ✅ Реализована поддержка тестового режима: тестовые платежи сохраняются в БД с фиктивным ID для тестирования статистики
- ✅ Добавлена функция `get_last_test_payment()` для обработки возвратов в тестовом режиме

**Версия:** 1.2.0  
**Последнее обновление:** 2024-11-18
