import logging
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import CallbackQuery

from keyboards.kb_builder import inline_builder_text

from lexicon.lexicon import (
    lexicon_buttons_border_camera_keys,
    lexicon_buttons_border_camera_values,
)


router = Router()
logger = logging.getLogger(__name__)
MINSK_TZ = ZoneInfo("Europe/Minsk")
CAMERA_MENU_BUTTON_TEXT = "В меню"
CAMERA_MENU_BUTTON_CALLBACK = "main_menu"

CAMERA_POINTS = {
    "warsaw_bridge": {
        "title": "Варшавский мост",
        "cameras": [
            ("въезд в Республику Беларусь", "https://www.customs.gov.by/webcam/brst112_c1.jpg"),
        ],
    },
    "berestovitsa": {
        "title": "Берестовица",
        "cameras": [
            ("выезд из Республики Беларусь", "https://www.customs.gov.by/webcam/gr02.jpg"),
            ("въезд в Республику Беларусь", "https://www.customs.gov.by/webcam/gr05.jpg"),
        ],
    },
    "bruzgi": {
        "title": "Брузги",
        "cameras": [
            ("выезд из Республики Беларусь", "https://www.customs.gov.by/webcam/gr01.jpg"),
            ("въезд в Республику Беларусь", "https://www.customs.gov.by/webcam/gr06.jpg"),
        ],
    },
    "kotlovka": {
        "title": "Котловка",
        "cameras": [
            ("выезд из Республики Беларусь", "https://www.customs.gov.by/webcam/OSH2.jpg"),
            ("въезд в Республику Беларусь", "https://www.customs.gov.by/webcam/OSH3.jpg"),
        ],
    },
    "kamenny_log": {
        "title": "Каменный Лог",
        "cameras": [
            ("выезд из Республики Беларусь", "https://www.customs.gov.by/webcam/OSH1.jpg"),
            ("въезд в Республику Беларусь", "https://www.customs.gov.by/webcam/OSH4.jpg"),
        ],
    },
    "privalka": {
        "title": "Привалка",
        "cameras": [
            ("выезд из Республики Беларусь", "https://www.customs.gov.by/webcam/gr03.jpg"),
            ("въезд в Республику Беларусь", "https://www.customs.gov.by/webcam/gr04.jpg"),
        ],
    },
    "benyakoni": {
        "title": "Бенякони",
        "cameras": [
            ("выезд из Республики Беларусь", "https://www.customs.gov.by/webcam/ben2.jpg"),
            ("въезд в Республику Беларусь", "https://www.customs.gov.by/webcam/ben1.jpg"),
        ],
    },
    "grigorovshchina": {
        "title": "Григоровщина",
        "cameras": [
            ("выезд из Республики Беларусь", "https://www.customs.gov.by/webcam/vt01.jpg"),
            ("въезд в Республику Беларусь", "https://www.customs.gov.by/webcam/vt02.jpg"),
        ],
    },
}


def _with_cache_buster(url: str) -> str:
    parsed_url = urlsplit(url)
    query_params = parse_qsl(parsed_url.query, keep_blank_values=True)
    query_params.append(("ts", str(int(datetime.now(MINSK_TZ).timestamp()))))
    return urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            urlencode(query_params),
            parsed_url.fragment,
        )
    )


class ShowCameraState(StatesGroup):
    border = State()


@router.callback_query(F.data == "show_camera", StateFilter(default_state))
async def process_callback_show_camera(callback: CallbackQuery, state: FSMContext):
    camera_buttons_text = [*lexicon_buttons_border_camera_values, CAMERA_MENU_BUTTON_TEXT]
    camera_buttons_callback = [*lexicon_buttons_border_camera_keys, CAMERA_MENU_BUTTON_CALLBACK]

    await callback.message.edit_text(
        "Выберите камеру 📸",
        reply_markup=inline_builder_text(
            text=camera_buttons_text,
            callback_data=camera_buttons_callback,
            sizes=[2, 2, 2, 2, 1],
        ),
    )

    await state.set_state(ShowCameraState.border)


@router.callback_query(
    F.data.in_(lexicon_buttons_border_camera_keys), StateFilter(ShowCameraState.border)
)
async def process_border_state(callback: CallbackQuery, state: FSMContext):
    await state.update_data(border=callback.data)

    data = await state.get_data()
    point_data = CAMERA_POINTS.get(data["border"])

    if point_data is None:
        await callback.message.answer(
            "Не удалось найти выбранный пункт пропуска. Попробуйте еще раз.",
            reply_markup=inline_builder_text(
                text="Главное меню",
                callback_data="main_menu",
            ),
        )
        await state.clear()
        return

    sent_images = 0
    current_time = datetime.now(MINSK_TZ).strftime("%d.%m.%Y %H:%M")

    for direction, camera_url in point_data["cameras"]:
        caption = (
            f"{point_data['title']} — {direction}\n"
            f"{current_time} (Минск)"
        )
        try:
            await callback.message.answer_photo(
                photo=_with_cache_buster(camera_url),
                caption=caption,
            )
            sent_images += 1
        except Exception:
            logger.exception(
                "Не удалось отправить изображение камеры %s (%s)",
                point_data["title"],
                direction,
            )

    if sent_images == 0:
        await callback.message.answer(
            "Сейчас не получилось загрузить фото с выбранного пункта. Попробуйте немного позже.",
        )

    await callback.message.answer(
        "Назад",
        reply_markup=inline_builder_text(
            text="Назад", callback_data="show_camera"
        ),
    )

    await state.clear()
