# telegram_bot.py
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Импортируем модели и функции из вашего проекта
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models import Vacancy, BoardCard, UserProfile, TelegramUser
from app.ai_agent import calculate_match_percentage


# ========== Вспомогательные функции ==========
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📋 Новые вакансии", callback_data="new_vacancies")],
        [InlineKeyboardButton("⭐ Избранное", callback_data="starred")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("🎯 Топ совпадений", callback_data="top_match")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_vacancy_keyboard(vacancy_id, current_status):
    """Клавиатура для выбора статуса вакансии"""
    status_map = {
        'new': '📋 Новая',
        'starred': '⭐ Избранное',
        'applied': '📨 Отклик',
        'interview': '🗓 Собеседование',
        'rejected': '❌ Отказ',
        'offer': '🎉 Оффер'
    }
    keyboard = []
    row = []
    for status, label in status_map.items():
        if status != current_status:
            # Правильный формат: vacancy_id должен быть полным ID
            row.append(InlineKeyboardButton(label, callback_data=f"set_status_{vacancy_id}_{status}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_{vacancy_id}")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


# ========== Команды ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    app = create_app()
    with app.app_context():
        existing = TelegramUser.query.filter_by(chat_id=chat_id).first()
        if not existing:
            new_user = TelegramUser(
                chat_id=chat_id,
                username=user.username,
                first_name=user.first_name,
                subscribed=True,
                notify_new=True,
                notify_match=True
            )
            db.session.add(new_user)
            db.session.commit()

    await update.message.reply_text(
        f"🤖 *VacBot* приветствует вас, {user.first_name}!\n\n"
        "Я помогу отслеживать вакансии и управлять откликами.\n\n"
        "📌 *Доступные команды:*\n"
        "/start – запуск бота\n"
        "/menu – открыть главное меню\n"
        "/stats – статистика\n"
        "/subscribe – подписаться на уведомления\n"
        "/unsubscribe – отписаться",
        parse_mode="Markdown"
    )
    await update.message.reply_text("🔽 Выберите действие:", reply_markup=get_main_keyboard())


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔽 Главное меню:", reply_markup=get_main_keyboard())


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = create_app()
    with app.app_context():
        total = Vacancy.query.count()
        new_count = BoardCard.query.filter_by(status='new').count()
        starred_count = BoardCard.query.filter_by(starred=True).count()
        applied_count = BoardCard.query.filter_by(status='applied').count()
        interview_count = BoardCard.query.filter_by(status='interview').count()
        rejected_count = BoardCard.query.filter_by(status='rejected').count()
        offer_count = BoardCard.query.filter_by(status='offer').count()

    msg = f"📊 *Статистика VacBot*\n\n"
    msg += f"📋 Всего вакансий: *{total}*\n\n"
    msg += f"🆕 Новые: {new_count}\n"
    msg += f"⭐ Избранное: {starred_count}\n"
    msg += f"📨 Отклик: {applied_count}\n"
    msg += f"🗓 Собеседование: {interview_count}\n"
    msg += f"❌ Отказ: {rejected_count}\n"
    msg += f"🎉 Оффер: {offer_count}"

    if isinstance(update, Update) and update.callback_query:
        await update.callback_query.message.edit_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    app = create_app()
    with app.app_context():
        user = TelegramUser.query.filter_by(chat_id=chat_id).first()
        if user:
            user.subscribed = True
            db.session.commit()
            await update.message.reply_text("✅ Вы подписались на уведомления о новых вакансиях!")
        else:
            await update.message.reply_text("❌ Сначала зарегистрируйтесь через /start")


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    app = create_app()
    with app.app_context():
        user = TelegramUser.query.filter_by(chat_id=chat_id).first()
        if user:
            user.subscribed = False
            db.session.commit()
            await update.message.reply_text("🔕 Вы отписались от уведомлений.")


# ========== Обработчики кнопок ==========
async def show_new_vacancies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    app = create_app()
    with app.app_context():
        vacancies = Vacancy.query.all()
        new_vacs = []
        for v in vacancies:
            v_dict = v.to_dict()
            if v_dict.get('board_status') == 'new':
                # Сохраняем полный ID вакансии
                new_vacs.append((v.id, v.title, v.company))

    if not new_vacs:
        await query.message.edit_text("🆕 Новых вакансий нет.", reply_markup=get_main_keyboard())
        return

    context.user_data['current_vacancies'] = new_vacs
    context.user_data['current_page'] = 0
    context.user_data['current_title'] = "🆕 Новые вакансии"
    await render_vacancy_page(query, "🆕 Новые вакансии", context)


async def show_starred(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    app = create_app()
    with app.app_context():
        starred_cards = BoardCard.query.filter_by(starred=True).all()
        vacancies = []
        for card in starred_cards:
            if card.vacancy:
                vacancies.append((card.vacancy.id, card.vacancy.title, card.vacancy.company))

    if not vacancies:
        await query.message.edit_text("⭐ Нет избранных вакансий.", reply_markup=get_main_keyboard())
        return

    context.user_data['current_vacancies'] = vacancies
    context.user_data['current_page'] = 0
    context.user_data['current_title'] = "⭐ Избранное"
    await render_vacancy_page(query, "⭐ Избранное", context)


async def render_vacancy_page(query, title, context):
    vacancies = context.user_data.get('current_vacancies', [])
    page = context.user_data.get('current_page', 0)
    context.user_data['current_title'] = title

    if not vacancies or page >= len(vacancies):
        return

    vac_id, vac_title, vac_company = vacancies[page]

    app = create_app()
    with app.app_context():
        match_percent = calculate_match_percentage(Vacancy.query.get(vac_id))
        vac = Vacancy.query.get(vac_id)
        status = vac.to_dict().get('board_status', 'new') if vac else 'new'

    msg = f"*{title}*\n\n"
    msg += f"📌 *{vac_title}*\n"
    msg += f"🏢 {vac_company}\n"
    msg += f"📊 Совпадение: *{match_percent}%*\n"
    msg += f"📋 Статус: {status}"

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data="prev_vacancy"))
    if page < len(vacancies) - 1:
        nav_buttons.append(InlineKeyboardButton("Вперёд ▶️", callback_data="next_vacancy"))

    keyboard = []
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("📝 Сменить статус", callback_data=f"status_menu_{vac_id}")])
    keyboard.append([InlineKeyboardButton("◀️ В меню", callback_data="back_to_menu")])

    await query.message.edit_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_top_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    app = create_app()
    with app.app_context():
        vacancies = Vacancy.query.all()
        vacs_with_match = [(v.id, v.title, v.company, calculate_match_percentage(v)) for v in vacancies]
        vacs_with_match.sort(key=lambda x: x[3], reverse=True)
        top5 = vacs_with_match[:5]

    if not top5:
        await query.message.edit_text("🎯 Вакансий с высоким совпадением не найдено.", reply_markup=get_main_keyboard())
        return

    msg = "🎯 *Топ вакансий по совпадению с профилем*\n\n"
    for _, title, company, match in top5:
        msg += f"• *{title}* – {match}%\n"
        msg += f"  {company}\n\n"
    await query.message.edit_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    app = create_app()
    with app.app_context():
        profile = UserProfile.query.first()

    if not profile or not profile.name:
        await query.message.edit_text("👤 Профиль не заполнен. Заполните его на веб-странице.",
                                      reply_markup=get_main_keyboard())
        return

    msg = f"👤 *Профиль пользователя*\n\n"
    msg += f"📛 Имя: {profile.name or '—'}\n"
    msg += f"🎓 Специальность: {profile.specialty or '—'}\n"
    msg += f"💼 Навыки: {profile.skills or '—'}\n"
    msg += f"⭐ Предпочтения: {profile.preferred_directions or '—'}"
    await query.message.edit_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id

    app = create_app()
    with app.app_context():
        user = TelegramUser.query.filter_by(chat_id=chat_id).first()
        if not user:
            await query.message.edit_text("Сначала зарегистрируйтесь через /start")
            return

        msg = f"⚙️ *Настройки*\n\n"
        msg += f"🔔 Уведомления о новых вакансиях: {'✅ Вкл' if user.notify_new else '❌ Выкл'}\n"
        msg += f"🎯 Уведомления о высоком совпадении: {'✅ Вкл' if user.notify_match else '❌ Выкл'}\n"
        msg += f"📊 Минимальный процент совпадения: {user.min_match_percent}%"

        keyboard = [
            [InlineKeyboardButton("🔔 Уведомления о новых", callback_data="toggle_notify_new")],
            [InlineKeyboardButton("🎯 Уведомления о совпадении", callback_data="toggle_notify_match")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")]
        ]
        await query.message.edit_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ========== Главный обработчик ==========
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "new_vacancies":
        await show_new_vacancies(update, context)
    elif data == "starred":
        await show_starred(update, context)
    elif data == "stats":
        await stats(update, context)
    elif data == "profile":
        await show_profile(update, context)
    elif data == "top_match":
        await show_top_match(update, context)
    elif data == "settings":
        await show_settings(update, context)
    elif data == "back_to_menu":
        await query.message.edit_text("🔽 Главное меню:", reply_markup=get_main_keyboard())
    elif data == "next_vacancy":
        context.user_data['current_page'] = context.user_data.get('current_page', 0) + 1
        title = context.user_data.get('current_title', "Вакансии")
        await render_vacancy_page(query, title, context)
    elif data == "prev_vacancy":
        context.user_data['current_page'] = context.user_data.get('current_page', 0) - 1
        title = context.user_data.get('current_title', "Вакансии")
        await render_vacancy_page(query, title, context)
    elif data.startswith("status_menu_"):
        vac_id = data.replace("status_menu_", "")
        app = create_app()
        with app.app_context():
            vac = Vacancy.query.get(vac_id)
            if vac:
                status = vac.to_dict().get('board_status', 'new')
                await query.message.edit_text(
                    f"Выберите новый статус для вакансии:\n\n*{vac.title}*",
                    parse_mode="Markdown",
                    reply_markup=get_vacancy_keyboard(vac_id, status)
                )
            else:
                await query.answer("❌ Вакансия не найдена!")
                await query.message.edit_text("❌ Вакансия не найдена в базе данных.", reply_markup=get_main_keyboard())
    elif data.startswith("set_status_"):
        parts = data.split("_")
        # Формат: set_status_{vacancy_id}_{new_status}
        # vacancy_id может содержать символы _, поэтому собираем все части между 3 и последней
        new_status = parts[-1]
        vac_id = "_".join(parts[2:-1])

        print(f"🔄 Меняем статус: vacancy_id={vac_id}, new_status={new_status}")

        app = create_app()
        with app.app_context():
            vacancy = Vacancy.query.get(vac_id)
            if not vacancy:
                await query.answer("❌ Вакансия не найдена!")
                await query.message.edit_text("❌ Ошибка: вакансия не найдена в базе данных.",
                                              reply_markup=get_main_keyboard())
                return

            card = BoardCard.query.filter_by(vacancy_id=vac_id).first()

            if card:
                if new_status == "starred":
                    card.starred = True
                    card.status = "starred"  # ← добавляем эту строку
                else:
                    if card.starred:
                        card.starred = False
                    card.status = new_status
                db.session.commit()
                await query.answer(f"✅ Статус изменён на {new_status}")
                await query.message.edit_text(
                    f"✅ Статус вакансии *{vacancy.title}* успешно изменён на *{new_status}*!",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            else:
                new_card = BoardCard(
                    vacancy_id=vac_id,
                    status=new_status if new_status != "starred" else "new",
                    starred=(new_status == "starred")
                )
                db.session.add(new_card)
                db.session.commit()
                await query.answer("✅ Карточка создана!")
                await query.message.edit_text(
                    f"✅ Статус вакансии *{vacancy.title}* успешно установлен на *{new_status}*!",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
    elif data.startswith("delete_"):
        vac_id = data.replace("delete_", "")
        app = create_app()
        with app.app_context():
            vacancy = Vacancy.query.get(vac_id)
            if vacancy:
                BoardCard.query.filter_by(vacancy_id=vac_id).delete()
                db.session.delete(vacancy)
                db.session.commit()
                await query.answer("Вакансия удалена")
                await query.message.edit_text("🗑️ Вакансия удалена", reply_markup=get_main_keyboard())
    elif data == "toggle_notify_new":
        chat_id = update.effective_chat.id
        app = create_app()
        with app.app_context():
            user = TelegramUser.query.filter_by(chat_id=chat_id).first()
            if user:
                user.notify_new = not user.notify_new
                db.session.commit()
        await show_settings(update, context)
    elif data == "toggle_notify_match":
        chat_id = update.effective_chat.id
        app = create_app()
        with app.app_context():
            user = TelegramUser.query.filter_by(chat_id=chat_id).first()
            if user:
                user.notify_match = not user.notify_match
                db.session.commit()
        await show_settings(update, context)


# ========== Запуск бота ==========
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🚀 Telegram-бот запущен...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())