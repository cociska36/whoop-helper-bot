from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, Filters, MessageHandler
from config import TELEGRAM_BOT_TOKEN
from whoop import start, info, refresh, get_code, button, handle_sheet_selection, get_date, handle_column_selection, schedule_refresh # Импортируем функции из основного файла
import threading

# Основная функция
def main():
    # Запускаем фоновой поток для выполнения задачи
    threading.Thread(target=schedule_refresh, daemon=True).start()
    # Инициализация бота
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Регистрация обработчиков команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("info", info))
    dp.add_handler(CommandHandler("refresh", refresh))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, get_code))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, get_date), group=1)  # Обработчик для даты
    
    # Обработчик нажатий на кнопки
    dp.add_handler(CallbackQueryHandler(button, pattern='auth'))  # Для авторизации
    dp.add_handler(CallbackQueryHandler(handle_sheet_selection, pattern='^(recovery|workout|sleep|cycles)$'))  # Для выбора листов
    dp.add_handler(CallbackQueryHandler(handle_column_selection, pattern=r'^(col_\d+|all_data)$')) # Для выбора данных # Для выбора данных
    
    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
