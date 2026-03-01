<div align="center">
  <img src="./assets/tournabout-ava.png" alt="TournaBot" width="180"/>

  <h1>TournaBot</h1>
  <p>Telegram-бот для проведения круговых турниров по настольному теннису</p>

  [![Deploy](https://github.com/LuminiteTime/Tournabot/actions/workflows/deploy.yml/badge.svg)](https://github.com/LuminiteTime/Tournabot/actions/workflows/deploy.yml)
  [![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
  [![aiogram](https://img.shields.io/badge/aiogram-3.25-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
  [![PostgreSQL](https://img.shields.io/badge/postgres-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
</div>

---

## Что умеет бот

- **Создание турнира** — задаёшь название и список игроков (4–12 человек)
- **Распределение по таблицам** — игроки раскидываются по таблицам (4–8 мест) змейкой с выбором формата
- **Раундовое расписание** — матчи выстраиваются по оптимальному порядку раундов; доступные матчи подсвечиваются зелёным
- **Интерактивная сетка** — вся таблица прямо в одном Telegram-сообщении в виде инлайн-клавиатуры
- **Ввод счётов** — нажал на доступный матч → матч начат (кнопка синяя) → нажал снова → ввёл счёт → таблица обновилась
- **Навигация между таблицами** — кнопки ◀ / ▶ для переключения
- **Расчёт мест** — 2 очка за победу, 1 за поражение; тайбрейк по соотношению мячей; ничьи разрешаются вручную через кнопки
- **Общий зачёт** — места из всех столов чередуются змейкой в итоговую таблицу
- **Экспорт результатов**:
  - 📊 Excel (`.xlsx`) — таблица матчей + столбцы очков/соотношения/места + лист «Общий зачёт»
  - 📁 JSON (`.json`) — для импорта в другие системы (Title, Start/End Date, список матчей)

---

## Требования

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/) v2
- Токен бота (получить у [@BotFather](https://t.me/BotFather))

---

## Локальный запуск

**1. Клонировать репозиторий**

```bash
git clone https://github.com/LuminiteTime/Tournabot.git
cd Tournabot
```

**2. Создать `.env` из примера и заполнить**

```bash
cp .env.example .env
```

```dotenv
BOT_TOKEN=your-telegram-bot-token-here
POSTGRES_USER=tournabot
POSTGRES_PASSWORD=strongpassword
POSTGRES_DB=tournabot
DATABASE_URL=postgresql+asyncpg://tournabot:strongpassword@db:5432/tournabot
```

> `DATABASE_URL` должен содержать те же `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

**3. Запустить**

```bash
docker compose up -d --build
```

**4. Открыть бота в Telegram и написать `/start`**

**Остановить:**

```bash
docker compose down
```

---

## Деплой (GitHub Actions)

Пуш в ветку `main` автоматически деплоит бота на self-hosted runner.

Добавить в **Settings → Secrets → Actions**:

| Secret | Описание |
|---|---|
| `BOT_TOKEN` | Токен Telegram-бота |
| `POSTGRES_USER` | Имя пользователя PostgreSQL |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL |
| `POSTGRES_DB` | Имя базы данных |
