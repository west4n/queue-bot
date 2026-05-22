from config_data.config import load_config

# Загружаем границы из конфига
_config = load_config()
LEXICON_BUTTONS_BORDERS: dict[str, str] = _config.borders

LEXICON_TEXT_START: dict[str, str] = {
    "greeting": "Добро пожаловать в бота для отслеживания \n"
    "<b>очереди на границе!</b> 👋🏻\n\n"
    "Вот что я умею:\n\n"
    "1. Могу показать очередь на границе\n"
    "2. Могу показать регистрацию первого автомобиля\n"
    "3. Могу отслеживать очередь ваших автомобилей\n\n"
    "Выберите, что вы хотите сделать:"
}

LEXICON_TEXT_SUPPORT: dict[str, str] = {
    "contact_card": (
        "По вопросам пишите в поддержку.\n\n"
        "Желательно приложить скрин, "
        "если есть ошибка."
    ),
    "unavailable": "Поддержка временно недоступна. Попробуйте позже.",
}

LEXICON_TEXT_IDEA: dict[str, str] = {
    "instruction": (
        "Опишите вашу идею одним сообщением.\n\n"
        "Можно отправить текст, фото, видео, документ или другое вложение."
    ),
    "thank_you": "Спасибо за идею! Мы передали ее администраторам.",
    "delivery_error": (
        "Спасибо за идею! Сейчас не удалось доставить ее администраторам.\n"
        "Мы уже зафиксировали событие, попробуйте отправить идею еще раз чуть позже."
    ),
}

LEXICON_COMMANDS: dict[str, str] = {
    "/start": "Главное меню",
    "/reset": "Если не работает команда /start",
}


LEXICON_BUTTONS_START: dict[str, str] = {
    "queue": "Узнать очередь на границе",
    "reg_car_first": "Статистика очереди",
}

LEXICON_BUTTONS_ADMIN: dict[str, str] = {"admin": "/чел. в базе"}


LEXICON_BUTTONS_ADD_CAR: dict[str, str] = {
    "add_car": "Добавить машину",
    "main_menu": "Вернуться на главную",
}

LEXICON_BUTTONS_TYPE_CAR: dict[str, str] = {
    "car_type": "Легковой автомобиль",
    "truck_type": "Грузовой автомобиль",
    "bus_type": "Автобус",
}

LEXICON_BUTTONS_MINUTES: dict[str, str] = {
    "5_min": "5 минут",
    "10_min": "10 минут",
    "15_min": "15 минут",
}

LEXICON_BUTTONS_CARS: dict[str, str] = {
    "15_cars": "15 машин",
    "30_cars": "30 машин",
}

LEXICON_BUTTONS_BORDER_CAMERA: dict[str, str] = {
    "warsaw_bridge": "Варшавский мост",
    "berestovitsa": "Берестовица",
    "bruzgi": "Брузги",
    "kotlovka": "Котловка",
    "kamenny_log": "Каменный Лог",
    "privalka": "Привалка",
    "benyakoni": "Бенякони",
    "grigorovshchina": "Григоровщина",
}

LEXICON_BUTTONS_BUY_CALL: dict[str, str] = {
    "buy_call": "Купить звонок",
    "start_tracking": "Продолжить без звонка",
}


lexicon_buttons_start_keys = list(LEXICON_BUTTONS_START.keys())
lexicon_buttons_start_values = list(LEXICON_BUTTONS_START.values())

lexicon_buttons_admin_keys = list(LEXICON_BUTTONS_ADMIN.keys())
lexicon_buttons_admin_values = list(LEXICON_BUTTONS_ADMIN.values())

lexicon_buttons_add_car_keys = list(LEXICON_BUTTONS_ADD_CAR.keys())
lexiocn_buttons_add_car_values = list(LEXICON_BUTTONS_ADD_CAR.values())

lexicon_buttons_borders_keys = list(LEXICON_BUTTONS_BORDERS.keys())
lexicon_buttons_borders_values = list(LEXICON_BUTTONS_BORDERS.values())

lexicon_buttons_type_car_keys = list(LEXICON_BUTTONS_TYPE_CAR.keys())
lexicon_buttons_type_car_values = list(LEXICON_BUTTONS_TYPE_CAR.values())

lexicon_buttons_minutes_keys = list(LEXICON_BUTTONS_MINUTES.keys())
lexicon_buttons_minutes_values = list(LEXICON_BUTTONS_MINUTES.values())

lexicon_buttons_cars_keys = list(LEXICON_BUTTONS_CARS.keys())
lexicon_buttons_cars_values = list(LEXICON_BUTTONS_CARS.values())

lexicon_buttons_border_camera_keys = list(LEXICON_BUTTONS_BORDER_CAMERA.keys())
lexicon_buttons_border_camera_values = list(
    LEXICON_BUTTONS_BORDER_CAMERA.values())
