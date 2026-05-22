"""
Функции для получения аналитики и статистики из базы данных
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from sqlalchemy import select, func, distinct, and_, or_, case
from sqlalchemy.dialects.postgresql import aggregate_order_by

from database.models import async_session, UserEvent, User, Payment


async def get_dau(target_date: Optional[date] = None) -> int:
    """
    Получить DAU (Daily Active Users) за указанную дату
    
    Args:
        target_date: Дата для подсчета DAU. Если None, используется сегодняшняя дата
    
    Returns:
        Количество уникальных пользователей за день
    """
    if target_date is None:
        target_date = date.today()
    
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        result = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        )
        return result or 0


async def get_mau(target_month: Optional[date] = None) -> int:
    """
    Получить MAU (Monthly Active Users) за указанный месяц
    
    Args:
        target_month: Дата в нужном месяце. Если None, используется текущий месяц
    
    Returns:
        Количество уникальных пользователей за месяц
    """
    if target_month is None:
        target_month = date.today()
    
    start_date = date(target_month.year, target_month.month, 1)
    if target_month.month == 12:
        end_date = date(target_month.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(target_month.year, target_month.month + 1, 1) - timedelta(days=1)
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        result = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        )
        return result or 0


async def get_wau(week_start: Optional[date] = None) -> int:
    """
    Получить WAU (Weekly Active Users) за указанную неделю
    
    Args:
        week_start: Дата начала недели (понедельник). Если None, используется начало текущей недели
    
    Returns:
        Количество уникальных пользователей за неделю
    """
    if week_start is None:
        today = date.today()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
    
    week_end = week_start + timedelta(days=6)
    
    start_datetime = datetime.combine(week_start, datetime.min.time())
    end_datetime = datetime.combine(week_end, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        result = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        )
        return result or 0


async def get_new_users(start_date: date, end_date: date) -> int:
    """
    Получить количество новых пользователей за период
    
    Args:
        start_date: Начало периода
        end_date: Конец периода
    
    Returns:
        Количество новых пользователей
    """
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        # Находим пользователей, у которых первое событие start в указанном периоде
        subquery = (
            select(
                UserEvent.tg_id,
                func.min(UserEvent.created_at).label('first_event')
            )
            .where(UserEvent.event_type == 'start')
            .group_by(UserEvent.tg_id)
            .having(
                and_(
                    func.min(UserEvent.created_at) >= start_datetime,
                    func.min(UserEvent.created_at) <= end_datetime
                )
            )
            .subquery()
        )
        
        result = await session.scalar(
            select(func.count(distinct(subquery.c.tg_id)))
        )
        return result or 0


async def get_retention_cohort(cohort_date: date, days: int) -> float:
    """
    Получить retention для когорты пользователей
    
    Args:
        cohort_date: Дата когорты (дата регистрации)
        days: Количество дней для расчета retention (1, 7, 30)
    
    Returns:
        Процент retention (0-100)
    """
    cohort_start = datetime.combine(cohort_date, datetime.min.time())
    cohort_end = datetime.combine(cohort_date, datetime.max.time().replace(microsecond=999999))
    retention_date = cohort_date + timedelta(days=days)
    retention_start = datetime.combine(retention_date, datetime.min.time())
    retention_end = datetime.combine(retention_date, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        # Пользователи, зарегистрированные в когорте
        cohort_users_subquery = (
            select(UserEvent.tg_id.label('tg_id'))
            .where(
                and_(
                    UserEvent.event_type == 'start',
                    UserEvent.created_at >= cohort_start,
                    UserEvent.created_at <= cohort_end
                )
            )
            .distinct()
            .subquery()
        )
        
        # Пользователи из когорты, активные через N дней
        active_users_subquery = (
            select(UserEvent.tg_id.label('tg_id'))
            .where(
                and_(
                    UserEvent.tg_id.in_(select(cohort_users_subquery.c.tg_id)),
                    UserEvent.created_at >= retention_start,
                    UserEvent.created_at <= retention_end
                )
            )
            .distinct()
            .subquery()
        )
        
        cohort_count = await session.scalar(
            select(func.count(cohort_users_subquery.c.tg_id))
        ) or 0
        
        if cohort_count == 0:
            return 0.0
        
        active_count = await session.scalar(
            select(func.count(active_users_subquery.c.tg_id))
        ) or 0
        
        return (active_count / cohort_count) * 100


async def get_churn_rate(start_date: date, end_date: date) -> float:
    """
    Получить процент ушедших пользователей (churn rate)
    
    Args:
        start_date: Начало периода
        end_date: Конец периода
    
    Returns:
        Процент churn rate (0-100)
    """
    period_start = datetime.combine(start_date, datetime.min.time())
    period_end = datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
    
    # Период для сравнения (предыдущий период такой же длины)
    period_length = (end_date - start_date).days + 1
    prev_start = start_date - timedelta(days=period_length)
    prev_end = start_date - timedelta(days=1)
    prev_start_dt = datetime.combine(prev_start, datetime.min.time())
    prev_end_dt = datetime.combine(prev_end, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        # Пользователи, активные в предыдущем периоде
        prev_active_subquery = (
            select(UserEvent.tg_id.label('tg_id'))
            .where(
                and_(
                    UserEvent.created_at >= prev_start_dt,
                    UserEvent.created_at <= prev_end_dt
                )
            )
            .distinct()
            .subquery()
        )
        
        # Пользователи, активные в текущем периоде
        current_active_subquery = (
            select(UserEvent.tg_id.label('tg_id'))
            .where(
                and_(
                    UserEvent.tg_id.in_(select(prev_active_subquery.c.tg_id)),
                    UserEvent.created_at >= period_start,
                    UserEvent.created_at <= period_end
                )
            )
            .distinct()
            .subquery()
        )
        
        prev_count = await session.scalar(
            select(func.count(prev_active_subquery.c.tg_id))
        ) or 0
        
        if prev_count == 0:
            return 0.0
        
        current_count = await session.scalar(
            select(func.count(current_active_subquery.c.tg_id))
        ) or 0
        
        churned = prev_count - current_count
        return (churned / prev_count) * 100


async def get_funnel(start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Получить воронку конверсий
    
    Args:
        start_date: Начало периода
        end_date: Конец периода
    
    Returns:
        Словарь с данными воронки
    """
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        # 1. Регистрация
        registered = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.event_type == 'start',
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        ) or 0
        
        # 2. Добавление первой машины
        added_car = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.event_type == 'add_car',
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        ) or 0
        
        # 3. Запуск отслеживания
        started_tracking = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.event_type == 'track_start',
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        ) or 0
        
        # 4. Покупка звонка
        bought_call = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.event_type == 'buy_call',
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        ) or 0
        
        # 5. Повторное использование (пользователи с >1 сессией)
        repeat_users_subquery = (
            select(UserEvent.tg_id.label('tg_id'))
            .where(
                and_(
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
            .group_by(UserEvent.tg_id)
            .having(func.count(distinct(func.date(UserEvent.created_at))) > 1)
            .subquery()
        )
        
        repeat_users = await session.scalar(
            select(func.count(repeat_users_subquery.c.tg_id))
        ) or 0
        
        return {
            'registered': registered,
            'added_car': added_car,
            'started_tracking': started_tracking,
            'bought_call': bought_call,
            'repeat_users': repeat_users,
            'conversion_rates': {
                'registered_to_added_car': (added_car / registered * 100) if registered > 0 else 0,
                'added_car_to_tracking': (started_tracking / added_car * 100) if added_car > 0 else 0,
                'tracking_to_call': (bought_call / started_tracking * 100) if started_tracking > 0 else 0,
                'repeat_usage': (repeat_users / registered * 100) if registered > 0 else 0,
            }
        }


async def get_feature_usage(start_date: date, end_date: date) -> Dict[str, int]:
    """
    Получить статистику использования функций
    
    Args:
        start_date: Начало периода
        end_date: Конец периода
    
    Returns:
        Словарь с количеством использований каждой функции
    """
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        result = await session.execute(
            select(
                UserEvent.event_type,
                func.count(UserEvent.id).label('count')
            )
            .where(
                and_(
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
            .group_by(UserEvent.event_type)
        )
        
        return {row.event_type: row.count for row in result}


async def get_engagement_metrics(start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Получить метрики engagement
    
    Args:
        start_date: Начало периода
        end_date: Конец периода
    
    Returns:
        Словарь с метриками engagement
    """
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        # Среднее количество действий на пользователя
        # Используем подзапрос для подсчета действий на пользователя, затем берем среднее
        actions_per_user_subquery = (
            select(
                UserEvent.tg_id,
                func.count(UserEvent.id).label('action_count')
            )
            .where(
                and_(
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
            .group_by(UserEvent.tg_id)
            .subquery()
        )
        
        avg_actions = await session.scalar(
            select(func.avg(actions_per_user_subquery.c.action_count))
        ) or 0
        
        # Средняя длительность сессии (время между первым и последним действием в день)
        # Упрощенная версия - считаем по дням
        session_subquery = (
            select(
                UserEvent.tg_id,
                func.date(UserEvent.created_at).label('event_date'),
                func.min(UserEvent.created_at).label('first_action'),
                func.max(UserEvent.created_at).label('last_action')
            )
            .where(
                and_(
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
            .group_by(UserEvent.tg_id, func.date(UserEvent.created_at))
            .subquery()
        )
        
        # Вычисляем длительность сессии в минутах
        duration_subquery = (
            select(
                func.extract('epoch', 
                    session_subquery.c.last_action - session_subquery.c.first_action
                ).label('duration_seconds')
            )
            .where(
                session_subquery.c.last_action != session_subquery.c.first_action
            )
            .subquery()
        )
        
        session_duration = await session.scalar(
            select(func.avg(duration_subquery.c.duration_seconds / 60.0))
        ) or 0
        
        # Пиковые часы активности
        peak_hours = await session.execute(
            select(
                func.extract('hour', UserEvent.created_at).label('hour'),
                func.count(UserEvent.id).label('count')
            )
            .where(
                and_(
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
            .group_by(func.extract('hour', UserEvent.created_at))
            .order_by(func.count(UserEvent.id).desc())
            .limit(5)
        )
        
        peak_hours_list = [{'hour': int(row.hour), 'count': row.count} for row in peak_hours]
        
        return {
            'avg_actions_per_user': round(float(avg_actions), 2),
            'avg_session_duration_minutes': round(float(session_duration), 2),
            'peak_hours': peak_hours_list
        }


async def get_advertiser_metrics(start_date: date, end_date: date) -> Dict[str, Any]:
    """
    Получить метрики для рекламодателей
    
    Args:
        start_date: Начало периода
        end_date: Конец периода
    
    Returns:
        Словарь с метриками для рекламодателей
    """
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        # Общее количество пользователей
        total_users = await session.scalar(select(func.count(User.tg_id))) or 0
        
        # DAU и MAU
        dau = await get_dau()
        mau = await get_mau()
        
        # Пользователи с добавленными машинами
        users_with_cars = await session.scalar(
            select(func.count(User.tg_id))
            .where(User.car_numbers.isnot(None))
        ) or 0
        
        # Пользователи, использующие отслеживание
        users_tracking = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.event_type == 'track_start',
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        ) or 0
        
        # Engagement Rate
        active_users = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        ) or 0
        
        engagement_rate = (active_users / total_users * 100) if total_users > 0 else 0
        
        # Conversion Rate - добавление машины
        registered = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.event_type == 'start',
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        ) or 0
        
        added_car = await session.scalar(
            select(func.count(distinct(UserEvent.tg_id)))
            .where(
                and_(
                    UserEvent.event_type == 'add_car',
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
        ) or 0
        
        conversion_rate = (added_car / registered * 100) if registered > 0 else 0
        
        # ARPU (Average Revenue Per User)
        total_revenue = await session.scalar(
            select(func.sum(Payment.amount))
            .where(
                and_(
                    Payment.payment_type == 'payment',
                    Payment.created_at >= start_datetime,
                    Payment.created_at <= end_datetime
                )
            )
        ) or 0
        
        arpu = (total_revenue / active_users) if active_users > 0 else 0
        
        # Популярные функции
        feature_usage = await get_feature_usage(start_date, end_date)
        popular_features = sorted(
            feature_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'total_users': total_users,
            'dau': dau,
            'mau': mau,
            'users_with_cars': users_with_cars,
            'users_with_cars_percent': (users_with_cars / total_users * 100) if total_users > 0 else 0,
            'users_tracking': users_tracking,
            'users_tracking_percent': (users_tracking / total_users * 100) if total_users > 0 else 0,
            'engagement_rate': round(engagement_rate, 2),
            'conversion_rate': round(conversion_rate, 2),
            'arpu': round(arpu, 2),
            'popular_features': [{'feature': f[0], 'count': f[1]} for f in popular_features]
        }


async def get_popular_borders(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """
    Получить популярные границы
    
    Args:
        start_date: Начало периода
        end_date: Конец периода
    
    Returns:
        Список границ с количеством просмотров
    """
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        # Создаем выражение для извлечения border_name из JSONB
        border_name_expr = UserEvent.event_data['border_name'].astext
        
        result = await session.execute(
            select(
                border_name_expr.label('border_name'),
                func.count(UserEvent.id).label('count')
            )
            .where(
                and_(
                    UserEvent.event_type.in_(['queue_view', 'queue_stats_view']),
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime,
                    UserEvent.event_data.isnot(None)
                )
            )
            .group_by(border_name_expr)
            .order_by(func.count(UserEvent.id).desc())
        )
        
        return [{'border_name': row.border_name, 'count': row.count} for row in result if row.border_name]


async def get_peak_hours(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """
    Получить пиковые часы активности
    
    Args:
        start_date: Начало периода
        end_date: Конец периода
    
    Returns:
        Список часов с количеством действий
    """
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time().replace(microsecond=999999))
    
    async with async_session() as session:
        result = await session.execute(
            select(
                func.extract('hour', UserEvent.created_at).label('hour'),
                func.count(UserEvent.id).label('count')
            )
            .where(
                and_(
                    UserEvent.created_at >= start_datetime,
                    UserEvent.created_at <= end_datetime
                )
            )
            .group_by(func.extract('hour', UserEvent.created_at))
            .order_by(func.count(UserEvent.id).desc())
        )
        
        return [{'hour': int(row.hour), 'count': row.count} for row in result]

