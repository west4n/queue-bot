import json
from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str


@dataclass
class db:
    base_url: str


@dataclass
class TwilioConfig:
    account_sid: str
    auth_token: str
    from_phone: str


@dataclass
class Config:
    tg_bot: TgBot
    db: db
    borders: dict[str, str]
    twilio: TwilioConfig
    call_star_price: int
    call_mode: str
    call_hangup_delay: int
    support_url: str


# Дефолтные значения границ для обратной совместимости
DEFAULT_BORDERS = {
    "53d94097-2b34-11ec-8467-ac1f6bf889c0": "Бенякони",
    "b60677d4-8a00-4f93-a781-e129e1692a03": "Каменный лог",
    "b7b368c7-d00c-11e7-a46c-001517da0c91": "Котловка",
    "ffe81c11-00d6-11e8-a967-b0dd44bde851": "Григоровщина",
    "a9173a85-3fc0-424c-84f0-defa632481e4": "Брест",
    "98b5be92-d3a5-4ba2-9106-76eb4eb3df49": "Козловичи",
    "b797d4d-706a-440f-a1a4-826c191e1e36": "Брузги",
    "7e46a2d1-ab2f-11ec-bafb-ac1f6bf889c1": "Берестовица",
}


def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)

    # Загрузка границ из .env или использование дефолтных значений
    borders_str = env.str("BORDERS", default="")
    if borders_str:
        try:
            borders = json.loads(borders_str)
        except json.JSONDecodeError:
            borders = DEFAULT_BORDERS
    else:
        borders = DEFAULT_BORDERS

    return Config(
        tg_bot=TgBot(token=env("BOT_TOKEN")),
        db=db(base_url=env("BASE_URL")),
        borders=borders,
        twilio=TwilioConfig(
            account_sid=env("TWILIO_ACCOUNT_SID", default=""),
            auth_token=env("TWILIO_AUTH_TOKEN", default=""),
            from_phone=env("TWILIO_FROM_PHONE", default=""),
        ),
        call_star_price=env.int("CALL_STAR_PRICE", default=100),
        call_mode=env.str("CALL_MODE", default="test"),
        call_hangup_delay=env.int("CALL_HANGUP_DELAY", default=5),
        support_url=env.str("SUPPORT_URL", default=""),
    )


ADMIN_IDS = [344786301, 538297748]
