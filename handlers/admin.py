import logging
from datetime import date, timedelta

import database.requests as req
import database.analytics_requests as analytics_req

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, MessageOriginChannel
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from filters.is_admin import IsAdmin

from config_data.config import ADMIN_IDS

from keyboards.kb_builder import inline_builder_text

from states.state_mail import CreateMessage, BindMenuContent

from lexicon.lexicon import lexicon_buttons_admin_keys, lexicon_buttons_admin_values

logger = logging.getLogger(__name__)
router = Router()


def build_admin_panel_markup(total_users: int | str):
    text_users = f"🙋‍♂️ {total_users}/чел. в базе"
    text_admin_mail = "Создать информационную рассылку"
    text_payment_stats = "Статистика платежей"
    text_analytics = "📊 Аналитика"
    text_bind_insurance = "Задать сообщение: Страховки"
    text_bind_transfer = "Задать сообщение: Инд. трансфер"

    return inline_builder_text(
        text=[
            text_users,
            text_admin_mail,
            text_payment_stats,
            text_analytics,
            text_bind_insurance,
            text_bind_transfer,
        ],
        callback_data=[
            "any",
            "text_admin_mail",
            "payment_statistics",
            "analytics_main",
            "bind_insurance_content",
            "bind_transfer_content",
        ],
        sizes=[1, 1, 2, 1, 1],
    )


def resolve_source_message_ids(message: Message) -> tuple[int, int]:
    if message.forward_from_chat and message.forward_from_message_id:
        return message.forward_from_chat.id, message.forward_from_message_id

    if isinstance(message.forward_origin, MessageOriginChannel):
        return message.forward_origin.chat.id, message.forward_origin.message_id

    return message.chat.id, message.message_id


@router.message(Command(commands="admin"), IsAdmin(ADMIN_IDS))
async def process_command_admin_start(message: Message):
    total_users = await req.get_total_users()

    await message.answer(
        "Привет админ! 💪🏻",
        reply_markup=build_admin_panel_markup(total_users),
    )


@router.callback_query(
    F.data == "any", IsAdmin(ADMIN_IDS)
)
async def process_callback_any(callback: CallbackQuery):
    """Обработчик для информационной кнопки (статистика пользователей)"""
    await callback.answer()


@router.callback_query(
    F.data == "text_admin_mail", IsAdmin(ADMIN_IDS), StateFilter(default_state)
)
async def process_callback_text_admin_mail(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "<b>Создание рассылки</b> ✉️\n\n" "Ниже отправьте тему рассылки:",
    )

    await state.set_state(CreateMessage.theme_text)


@router.callback_query(
    F.data == "payment_statistics", IsAdmin(ADMIN_IDS)
)
async def process_callback_payment_statistics(callback: CallbackQuery):
    """Отображение статистики платежей"""
    try:
        stats = await req.get_payment_statistics()
        
        # Форматируем статистику
        text = (
            "<b>📊 Статистика платежей</b>\n\n"
            f"⭐ Получено звезд: <b>{stats['total_payments']}</b>\n"
            f"↩️ Возвращено звезд: <b>{stats['total_refunds']}</b>\n"
            f"💰 Чистая сумма: <b>{stats['net_amount']}</b> звезд\n"
            f"💵 В долларах: <b>${stats['usd_amount']:.2f}</b>\n\n"
            f"<i>Курс: 1 звезда = $0.013</i>"
        )
        
        await callback.message.answer(
            text,
            reply_markup=inline_builder_text(
                text="Вернуться в админ-панель",
                callback_data="admin_back",
            ),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении статистики платежей: {e}")
        await callback.message.answer(
            "Ошибка при получении статистики платежей.",
            reply_markup=inline_builder_text(
                text="Вернуться в админ-панель",
                callback_data="admin_back",
            ),
        )
        await callback.answer()


@router.callback_query(
    F.data == "admin_back", IsAdmin(ADMIN_IDS)
)
async def process_callback_admin_back(callback: CallbackQuery, state: FSMContext):
    """Возврат в админ-панель"""
    await state.clear()
    total_users = await req.get_total_users()

    try:
        await callback.message.edit_text(
            "Привет админ! 💪🏻",
            reply_markup=build_admin_panel_markup(total_users),
        )
    except:
        await callback.message.answer(
            "Привет админ! 💪🏻",
            reply_markup=build_admin_panel_markup(total_users),
        )
    await callback.answer()


@router.callback_query(
    F.data == "bind_insurance_content", IsAdmin(ADMIN_IDS), StateFilter(default_state)
)
async def process_callback_bind_insurance_content(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "<b>Привязка кнопки \"Страховки\"</b>\n\n"
        "Перешлите сообщение рекламодателя (лучше именно forward), "
        "которое нужно показывать пользователю.",
        reply_markup=inline_builder_text(
            text="Отменить",
            callback_data="admin_back",
        ),
    )
    await state.set_state(BindMenuContent.insurance_message)


@router.callback_query(
    F.data == "bind_transfer_content", IsAdmin(ADMIN_IDS), StateFilter(default_state)
)
async def process_callback_bind_transfer_content(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "<b>Привязка кнопки \"Инд. трансфер\"</b>\n\n"
        "Перешлите сообщение рекламодателя (лучше именно forward), "
        "которое нужно показывать пользователю.",
        reply_markup=inline_builder_text(
            text="Отменить",
            callback_data="admin_back",
        ),
    )
    await state.set_state(BindMenuContent.transfer_message)


@router.message(BindMenuContent.insurance_message, IsAdmin(ADMIN_IDS))
async def process_bind_insurance_message(message: Message, state: FSMContext):
    if message.has_protected_content:
        await message.answer(
            "Это сообщение защищено от копирования.\n\n"
            "Отправьте, пожалуйста, тот же контент без защиты.",
            reply_markup=inline_builder_text(
                text="Отменить",
                callback_data="admin_back",
            ),
        )
        return

    source_chat_id, source_message_id = resolve_source_message_ids(message)
    await req.set_menu_content("insurance", source_chat_id, source_message_id)
    await state.clear()
    await message.answer(
        "Сообщение для кнопки <b>Страховки</b> сохранено.",
        reply_markup=inline_builder_text(
            text="Вернуться в админ-панель",
            callback_data="admin_back",
        ),
    )


@router.message(BindMenuContent.transfer_message, IsAdmin(ADMIN_IDS))
async def process_bind_transfer_message(message: Message, state: FSMContext):
    if message.has_protected_content:
        await message.answer(
            "Это сообщение защищено от копирования.\n\n"
            "Отправьте, пожалуйста, тот же контент без защиты.",
            reply_markup=inline_builder_text(
                text="Отменить",
                callback_data="admin_back",
            ),
        )
        return

    source_chat_id, source_message_id = resolve_source_message_ids(message)
    await req.set_menu_content("individual_transfer", source_chat_id, source_message_id)
    await state.clear()
    await message.answer(
        "Сообщение для кнопки <b>Инд. трансфер</b> сохранено.",
        reply_markup=inline_builder_text(
            text="Вернуться в админ-панель",
            callback_data="admin_back",
        ),
    )


# ========== АНАЛИТИКА ==========

@router.callback_query(
    F.data == "analytics_main", IsAdmin(ADMIN_IDS)
)
async def process_callback_analytics_main(callback: CallbackQuery):
    """Главная страница аналитики"""
    try:
        today = date.today()
        dau = await analytics_req.get_dau(today)
        mau = await analytics_req.get_mau()
        new_users_today = await analytics_req.get_new_users(today, today)
        
        text = (
            "<b>📊 Аналитика</b>\n\n"
            f"👥 DAU (сегодня): <b>{dau}</b>\n"
            f"👥 MAU (этот месяц): <b>{mau}</b>\n"
            f"🆕 Новые пользователи (сегодня): <b>{new_users_today}</b>\n\n"
            "Выберите раздел:"
        )
        
        await callback.message.answer(
            text,
            reply_markup=inline_builder_text(
                text=[
                    "👥 Пользователи",
                    "📈 Активность",
                    "🔄 Воронка",
                    "💰 Для рекламодателей",
                    "⬅️ Назад"
                ],
                callback_data=[
                    "analytics_users",
                    "analytics_activity",
                    "analytics_funnel",
                    "analytics_advertisers",
                    "admin_back"
                ],
            ),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении аналитики: {e}", exc_info=True)
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await callback.message.answer(
            f"❌ Ошибка при получении аналитики:\n\n<code>{error_msg[:200]}</code>",
            reply_markup=inline_builder_text(
                text="Назад",
                callback_data="admin_back",
            ),
        )
        await callback.answer()


@router.callback_query(
    F.data == "analytics_users", IsAdmin(ADMIN_IDS)
)
async def process_callback_analytics_users(callback: CallbackQuery):
    """Статистика пользователей"""
    try:
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        dau = await analytics_req.get_dau(today)
        wau = await analytics_req.get_wau()
        mau = await analytics_req.get_mau()
        
        # Retention
        retention_1d = await analytics_req.get_retention_cohort(yesterday, 1)
        retention_7d = await analytics_req.get_retention_cohort(week_ago, 7)
        retention_30d = await analytics_req.get_retention_cohort(month_ago, 30)
        
        # Churn rate
        churn_rate = await analytics_req.get_churn_rate(week_ago, today)
        
        # Новые пользователи
        new_users_week = await analytics_req.get_new_users(week_ago, today)
        new_users_month = await analytics_req.get_new_users(month_ago, today)
        
        text = (
            "<b>👥 Статистика пользователей</b>\n\n"
            f"<b>Активность:</b>\n"
            f"• DAU (сегодня): <b>{dau}</b>\n"
            f"• WAU (неделя): <b>{wau}</b>\n"
            f"• MAU (месяц): <b>{mau}</b>\n\n"
            f"<b>Новые пользователи:</b>\n"
            f"• За неделю: <b>{new_users_week}</b>\n"
            f"• За месяц: <b>{new_users_month}</b>\n\n"
            f"<b>Retention:</b>\n"
            f"• 1 день: <b>{retention_1d:.1f}%</b>\n"
            f"• 7 дней: <b>{retention_7d:.1f}%</b>\n"
            f"• 30 дней: <b>{retention_30d:.1f}%</b>\n\n"
            f"<b>Churn Rate:</b> <b>{churn_rate:.1f}%</b>"
        )
        
        await callback.message.answer(
            text,
            reply_markup=inline_builder_text(
                text="⬅️ Назад",
                callback_data="analytics_main",
            ),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении статистики пользователей: {e}", exc_info=True)
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await callback.message.answer(
            f"❌ Ошибка при получении статистики пользователей:\n\n<code>{error_msg[:200]}</code>",
            reply_markup=inline_builder_text(
                text="Назад",
                callback_data="analytics_main",
            ),
        )
        await callback.answer()


@router.callback_query(
    F.data == "analytics_activity", IsAdmin(ADMIN_IDS)
)
async def process_callback_analytics_activity(callback: CallbackQuery):
    """Метрики активности"""
    try:
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        engagement = await analytics_req.get_engagement_metrics(week_ago, today)
        feature_usage = await analytics_req.get_feature_usage(week_ago, today)
        popular_borders = await analytics_req.get_popular_borders(week_ago, today)
        
        # Форматируем популярные функции
        features_text = "\n".join([
            f"• {k}: <b>{v}</b>" for k, v in sorted(
                feature_usage.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        ])
        
        # Форматируем популярные границы
        borders_text = "\n".join([
            f"• {b['border_name']}: <b>{b['count']}</b>" 
            for b in popular_borders[:5]
        ]) if popular_borders else "Нет данных"
        
        # Пиковые часы
        peak_hours_text = "\n".join([
            f"• {h['hour']:02d}:00 - <b>{h['count']}</b> действий"
            for h in engagement.get('peak_hours', [])[:5]
        ]) if engagement.get('peak_hours') else "Нет данных"
        
        text = (
            "<b>📈 Активность</b>\n\n"
            f"<b>Engagement:</b>\n"
            f"• Среднее действий на пользователя: <b>{engagement.get('avg_actions_per_user', 0)}</b>\n"
            f"• Средняя длительность сессии: <b>{engagement.get('avg_session_duration_minutes', 0)}</b> мин\n\n"
            f"<b>Пиковые часы:</b>\n{peak_hours_text}\n\n"
            f"<b>Популярные функции:</b>\n{features_text}\n\n"
            f"<b>Популярные границы:</b>\n{borders_text}"
        )
        
        await callback.message.answer(
            text,
            reply_markup=inline_builder_text(
                text="⬅️ Назад",
                callback_data="analytics_main",
            ),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении метрик активности: {e}", exc_info=True)
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await callback.message.answer(
            f"❌ Ошибка при получении метрик активности:\n\n<code>{error_msg[:200]}</code>",
            reply_markup=inline_builder_text(
                text="Назад",
                callback_data="analytics_main",
            ),
        )
        await callback.answer()


@router.callback_query(
    F.data == "analytics_funnel", IsAdmin(ADMIN_IDS)
)
async def process_callback_analytics_funnel(callback: CallbackQuery):
    """Воронка конверсий"""
    try:
        today = date.today()
        month_ago = today - timedelta(days=30)
        
        funnel = await analytics_req.get_funnel(month_ago, today)
        rates = funnel['conversion_rates']
        
        text = (
            "<b>🔄 Воронка конверсий</b>\n"
            f"<i>(за последние 30 дней)</i>\n\n"
            f"1️⃣ Регистрация: <b>{funnel['registered']}</b>\n"
            f"   ↓ {rates['registered_to_added_car']:.1f}%\n"
            f"2️⃣ Добавление машины: <b>{funnel['added_car']}</b>\n"
            f"   ↓ {rates['added_car_to_tracking']:.1f}%\n"
            f"3️⃣ Запуск отслеживания: <b>{funnel['started_tracking']}</b>\n"
            f"   ↓ {rates['tracking_to_call']:.1f}%\n"
            f"4️⃣ Покупка звонка: <b>{funnel['bought_call']}</b>\n\n"
            f"5️⃣ Повторное использование: <b>{funnel['repeat_users']}</b> ({rates['repeat_usage']:.1f}%)"
        )
        
        await callback.message.answer(
            text,
            reply_markup=inline_builder_text(
                text="⬅️ Назад",
                callback_data="analytics_main",
            ),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении воронки: {e}", exc_info=True)
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await callback.message.answer(
            f"❌ Ошибка при получении воронки:\n\n<code>{error_msg[:200]}</code>",
            reply_markup=inline_builder_text(
                text="Назад",
                callback_data="analytics_main",
            ),
        )
        await callback.answer()


@router.callback_query(
    F.data == "analytics_advertisers", IsAdmin(ADMIN_IDS)
)
async def process_callback_analytics_advertisers(callback: CallbackQuery):
    """Метрики для рекламодателей"""
    try:
        today = date.today()
        month_ago = today - timedelta(days=30)
        
        metrics = await analytics_req.get_advertiser_metrics(month_ago, today)
        
        # Форматируем популярные функции
        features_text = "\n".join([
            f"• {f['feature']}: <b>{f['count']}</b> использований"
            for f in metrics.get('popular_features', [])[:5]
        ]) if metrics.get('popular_features') else "Нет данных"
        
        text = (
            "<b>💰 Метрики для рекламодателей</b>\n"
            f"<i>(за последние 30 дней)</i>\n\n"
            f"<b>Аудитория:</b>\n"
            f"• Всего пользователей: <b>{metrics['total_users']}</b>\n"
            f"• DAU: <b>{metrics['dau']}</b>\n"
            f"• MAU: <b>{metrics['mau']}</b>\n"
            f"• Engagement Rate: <b>{metrics['engagement_rate']}%</b>\n\n"
            f"<b>Конверсии:</b>\n"
            f"• Пользователи с машинами: <b>{metrics['users_with_cars']}</b> ({metrics['users_with_cars_percent']:.1f}%)\n"
            f"• Используют отслеживание: <b>{metrics['users_tracking']}</b> ({metrics['users_tracking_percent']:.1f}%)\n"
            f"• Conversion Rate: <b>{metrics['conversion_rate']}%</b>\n\n"
            f"<b>Монетизация:</b>\n"
            f"• ARPU: <b>{metrics['arpu']}</b> звезд\n\n"
            f"<b>Популярные функции:</b>\n{features_text}"
        )
        
        await callback.message.answer(
            text,
            reply_markup=inline_builder_text(
                text="⬅️ Назад",
                callback_data="analytics_main",
            ),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении метрик для рекламодателей: {e}", exc_info=True)
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await callback.message.answer(
            f"❌ Ошибка при получении метрик для рекламодателей:\n\n<code>{error_msg[:200]}</code>",
            reply_markup=inline_builder_text(
                text="Назад",
                callback_data="analytics_main",
            ),
        )
        await callback.answer()
