import requests
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import gspread
import uuid
from oauth2client.service_account import ServiceAccountCredentials
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, Filters, MessageHandler
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTH_URL, TOKEN_URL, SCOPE
from data_processing import (flatten_user_data,get_recovery_data,flatten_recovery_data,get_all_workouts,flatten_workout_data,get_all_sleep_sessions,flatten_sleep_data,get_all_cycles,flatten_cycles_data)
import psycopg2
import schedule

# Глобальная переменная для хранения кода авторизации
auth_code = None
selected_date = None
fl = 0

# Сохранение токенов в БД
def save_user_tokens(telegram_id, whoop_id, access_token, refresh_token):
    # Авторизация и подключение к Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('whoop-439019-6c624110dac0.json', scope)
    client = gspread.authorize(creds)

    # Открываем таблицу
    spreadsheet = client.open("whoop")
    worksheet = spreadsheet.worksheet("tokens")

    # Проверяем, существует ли запись для этого пользователя
    existing_records = worksheet.get_all_records()
    
    user_exists = False
    row_number = None

    for index, record in enumerate(existing_records, start=2):  # Начинаем с 2, потому что 1 строка — заголовки
        if str(record['telegram_id']) == str(telegram_id):
            user_exists = True
            row_number = index
            break

    if user_exists:
        if whoop_id is None or whoop_id == "":
            print("Ошибка: whoop_id недопустимо")
            return
        if row_number is None:
            print("Ошибка: не найдено соответствие для telegram_id")
            return

        # Обновляем существующую запись
        worksheet.update(f'B{row_number}', [[whoop_id]])
        worksheet.update(f'C{row_number}', [[access_token]])
        worksheet.update(f'D{row_number}', [[refresh_token]])
    else:
        # Вставляем новую строку
        worksheet.append_row([telegram_id, whoop_id, access_token, refresh_token])

# Получение токенов из БД
def get_user_tokens(telegram_id):

    # Авторизация и подключение к Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('whoop-439019-6c624110dac0.json', scope)
    client = gspread.authorize(creds)

    # Открываем таблицу
    spreadsheet = client.open("whoop")
    worksheet = spreadsheet.worksheet("tokens")

    # Получаем все данные
    existing_records = worksheet.get_all_records()

    # Ищем запись по telegram_id
    for record in existing_records:
        if str(record['telegram_id']) == str(telegram_id):
            access_token = record['access_token']
            refresh_token = record['refresh_token']
            return access_token, refresh_token
    
    # Если не найдено, возвращаем None
    return None, None

# Получение whoop_id из БД по telegram_id
def get_user_whoop_id(telegram_id):
    # Авторизация и подключение к Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('whoop-439019-6c624110dac0.json', scope)
    client = gspread.authorize(creds)

    # Открываем таблицу
    spreadsheet = client.open("whoop")
    worksheet = spreadsheet.worksheet("tokens")

    # Получаем все данные
    existing_records = worksheet.get_all_records()

    # Ищем запись по telegram_id
    for record in existing_records:
        if str(record['telegram_id']) == str(telegram_id):
            return record['whoop_id']
    
    # Если не найдено, возвращаем None
    return None



class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query_components = parse_qs(urlparse(self.path).query)
        if 'code' in query_components:
            auth_code = query_components['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization successful! You can close this tab.</h1></body></html>")
        else:
            self.send_response(400)
            self.end_headers()

def get_authorization_url():
    state = str(uuid.uuid4())
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI, 
        "response_type": "code",
        "scope": SCOPE,
        "state": state
    }
    return f"{AUTH_URL}?{urlencode(params)}"

def get_access_token(auth_code):
    if not (CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, auth_code):
        print("Ошибка: Не все параметры заданы!")
        return None, None

    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "offline"
    }

    try:
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()

        response_data = response.json()
        access_token = response_data.get('access_token')
        refresh_token = response_data.get('refresh_token')

        if access_token and refresh_token:
            return access_token, refresh_token
        else:
            print("Не удалось получить токены:", response_data)
            return None, None

    except requests.exceptions.HTTPError as err:
        print(f"Ошибка HTTP при получении токена: {err.response.status_code}, {err.response.text}")
    except Exception as ex:
        print(f"Произошла ошибка: {ex}")

    return None, None

    
def refresh_access_token(refresh_token):
    url = "https://api.prod.whoop.com/oauth/oauth2/token"
    print(refresh_token)
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "offline"
    }
    print(payload)
    try:
        # Изменено на data вместо json для правильной отправки данных
        response = requests.post(url, data=payload)
        response.raise_for_status()  # Поднимает исключение для статусов 4xx и 5xx
        return response.json()["access_token"], response.json().get("refresh_token")
    except requests.exceptions.HTTPError as err:
        print(f"Ошибка получения токена: {err}")
        print(f"Ответ: {response.text}")
        return None, None

def get_us_data(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    url = "https://api.prod.whoop.com/developer/v1/user/profile/basic"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        recovery_data = response.json()
        return recovery_data
    else:
        print("Error:", response.status_code, response.text)

def write_to_google_sheets(data, sheet_name, unique_keys):

    # Авторизация и подключение
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('whoop-439019-6c624110dac0.json', scope)
    client = gspread.authorize(creds)

    # Открытие таблицы и конкретного листа
    spreadsheet = client.open("whoop")
    worksheet = spreadsheet.worksheet(sheet_name)

    # Получаем все текущие данные из таблицы
    existing_data = worksheet.get_all_values()

    # Получаем уникальные ключи из существующих данных (по столбцам, которые указаны как уникальные)
    existing_keys = set(tuple(str(row[key]) for key in unique_keys) for row in existing_data[1:])  # Приводим к строкам

    new_data = []
    for row in data:
        # Извлекаем уникальные ключи для текущей строки данных и приводим их к строкам
        row_keys = tuple(str(row[key]) for key in unique_keys)

        # Если такой ключ уже существует, пропускаем эту строку
        if row_keys in existing_keys:
            continue

        # Если данных нет, добавляем строку в список для записи
        new_data.append(row)

    # Запись новых данных, если они есть
    if new_data:
        current_row = len(existing_data) + 1
        for row in new_data:
            worksheet.insert_row(row, current_row)
            current_row += 1
            time.sleep(1)  # Пауза в 1 секунду между запросами

# Telegram Bot Handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Для авторизации нажмите на кнопку ниже.")
    
    # Кнопка для авторизации
    keyboard = [[InlineKeyboardButton("Авторизоваться", callback_data="auth")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Нажмите кнопку для авторизации.", reply_markup=reply_markup)

# Обработчик кнопки авторизации
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == "auth":
        handle_auth(update, context)
    else:
        return

# Функция для обработки авторизации
def handle_auth(update: Update, context: CallbackContext):
    global fl
    fl = 1
    # Генерация ссылки для авторизации
    authorization_url = get_authorization_url()
    
    # Отправляем ссылку пользователю
    update.callback_query.message.reply_text(
        f"Для авторизации перейдите по ссылке и после авторизации отправьте полученный код сюда:\n{authorization_url}"
    )
    
    # Бот будет ожидать код от пользователя в следующем сообщении
    update.callback_query.message.reply_text("После авторизации введите полученный код здесь.")

def refresh_all_users_data():
    # Авторизация и подключение к Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('whoop-439019-6c624110dac0.json', scope)
    client = gspread.authorize(creds)

    # Открываем таблицу, где хранятся access_token для всех пользователей
    spreadsheet = client.open("whoop")
    tokens_worksheet = spreadsheet.worksheet("tokens")  # Лист, где хранятся токены пользователей
    
    # Получаем все данные из листа
    users_tokens = tokens_worksheet.get_all_values()

    # Итерируем по каждому пользователю и обновляем его данные
    for row_num, row in enumerate(users_tokens[1:], start=2):  # Пропускаем заголовок, начинаем с 2
        user_id = row[1]  # user_id пользователя
        access_token = row[2]  # access_token пользователя
        refresh_token = row[3]  # refresh_token пользователя

        # Если токен не найден, пропускаем пользователя
        if not access_token:
            print(f"Токен не найден для user_id {user_id}, пропуск...")
            continue

        # Проверяем, действителен ли access_token
        recovery_data = get_recovery_data(access_token)
        if recovery_data is None:  # Если access_token недействителен
            print(f"Access token недействителен для user_id {user_id}. Попытка обновления...")
            new_access_token, new_refresh_token = refresh_access_token(refresh_token)
            if new_access_token:
                access_token = new_access_token
                refresh_token = new_refresh_token
                # Обновляем токены в таблице
                tokens_worksheet.update_cell(row_num, 2, access_token)  # Обновляем access_token
                tokens_worksheet.update_cell(row_num, 3, refresh_token)  # Обновляем refresh_token
            else:
                print(f"Не удалось обновить access token для user_id {user_id}.")
                continue  # Пропускаем пользователя, если не удалось обновить токен

        # Получаем данные о восстановлении
        recovery_data = get_recovery_data(access_token)
        if recovery_data:
            flat_recovery_data = flatten_recovery_data(recovery_data)
            write_to_google_sheets(flat_recovery_data, "recovery", [0, 1])  # Пример уникальных ключей - cycle_id, sleep_id

        # Получаем данные о тренировках
        workouts_data = get_all_workouts(access_token)
        if workouts_data:
            flat_workout_data = flatten_workout_data(workouts_data)
            write_to_google_sheets(flat_workout_data, "workout", [0])  # Пример уникального ключа - id

        # Получаем данные о сне
        sleep_data = get_all_sleep_sessions(access_token)
        if sleep_data:
            flat_sleep_data = flatten_sleep_data(sleep_data)
            write_to_google_sheets(flat_sleep_data, "sleep", [0])  # Пример уникального ключа - id

        # Получаем данные о циклах
        cycles_data = get_all_cycles(access_token)
        if cycles_data:
            flat_cycles_data = flatten_cycles_data(cycles_data)
            write_to_google_sheets(flat_cycles_data, "cycles", [0])  # Пример уникального ключа - id

        print(f"Данные успешно обновлены для user_id {user_id}.")

# Функция для периодического выполнения обновления данных
def schedule_refresh(): 
    schedule.every().day.at("00:00").do(refresh_all_users_data) # Обновление каждый день в полночь
    while True:
        schedule.run_pending()
        time.sleep(1)  # Пауза между проверками расписания

# Обработчик сообщения от пользователя для получения кода авторизации
def get_code(update: Update, context: CallbackContext):
    global fl
    if fl == 1:
        global auth_code, user_id
        auth_code = update.message.text.strip()  # Получаем введённый пользователем код

        telegram_id = update.message.from_user.id

        # Получаем access_token и refresh_token
        access_token, refresh_token = get_access_token(auth_code)
        
        if access_token and refresh_token:
            user_data = get_us_data(access_token)
            user_id = flatten_user_data(user_data)
            save_user_tokens(telegram_id, user_id, access_token, refresh_token)
            context.user_data['access_token'] = access_token
            context.user_data['refresh_token'] = refresh_token  # Сохраняем refresh_token
            fl = 0
            update.message.reply_text("Авторизация прошла успешно! Теперь получаем данные и записываем их в Google Sheets.")

            access_token, refresh_token = get_user_tokens(telegram_id)

            if access_token:
                # Получаем данные о восстановлении и записываем их в таблицу
                recovery_data = get_recovery_data(access_token)
                if recovery_data:
                    flat_recovery_data = flatten_recovery_data(recovery_data)
                    write_to_google_sheets(flat_recovery_data, "recovery", [0, 1])  # Пример уникальных ключей - cycle_id, sleep_id

                # Получаем данные о тренировках
                workouts_data = get_all_workouts(access_token)
                if workouts_data:
                    flat_workout_data = flatten_workout_data(workouts_data)
                    write_to_google_sheets(flat_workout_data, "workout", [0])  # Пример уникального ключа - id

                # Получаем данные о сне
                sleep_data = get_all_sleep_sessions(access_token)
                if sleep_data:
                    flat_sleep_data = flatten_sleep_data(sleep_data)
                    write_to_google_sheets(flat_sleep_data, "sleep", [0])  # Пример уникального ключа - id

                # Получаем данные о циклах
                cycles_data = get_all_cycles(access_token)
                if cycles_data:
                    flat_cycles_data = flatten_cycles_data(cycles_data)
                    write_to_google_sheets(flat_cycles_data, "cycles", [0])  # Пример уникального ключа - id

                update.message.reply_text("Данные успешно записаны в Google Sheets!")
            else:
                update.message.reply_text("Ошибка: токены не найдены для вашего аккаунта.")
        else:
            update.message.reply_text("Ошибка при авторизации. Проверьте код и повторите.")

# Команда /refresh для обновления данных пользователя
def refresh(update: Update, context: CallbackContext):
    telegram_id = update.message.from_user.id  # Получаем идентификатор пользователя Telegram
    access_token, refresh_token = get_user_tokens(telegram_id)  # Используем telegram_id для получения токенов
    us_id = get_user_whoop_id(telegram_id)

    if access_token is None:
        update.message.reply_text("Ошибка: токен не найден.")
        return

    new_access_token, new_refresh_token = refresh_access_token(refresh_token)

    if new_access_token:
        # Обновляем токены в БД
        save_user_tokens(telegram_id, us_id, new_access_token, new_refresh_token)
        update.message.reply_text("Токены успешно обновлены!")
    else:
        update.message.reply_text("Ошибка при обновлении токенов.")
    
    access_token, refresh_token = get_user_tokens(telegram_id)
    # Получаем данные о восстановлении
    recovery_data = get_recovery_data(access_token)
    if recovery_data:
        flat_recovery_data = flatten_recovery_data(recovery_data)
        write_to_google_sheets(flat_recovery_data, "recovery", [0, 1])  # Пример уникальных ключей - cycle_id, sleep_id

    # Получаем данные о тренировках
    workouts_data = get_all_workouts(access_token)
    if workouts_data:
        flat_workout_data = flatten_workout_data(workouts_data)
        write_to_google_sheets(flat_workout_data, "workout", [0])  # Пример уникального ключа - id

    # Получаем данные о сне
    sleep_data = get_all_sleep_sessions(access_token)
    if sleep_data:
        flat_sleep_data = flatten_sleep_data(sleep_data)
        write_to_google_sheets(flat_sleep_data, "sleep", [0])  # Пример уникального ключа - id

    # Получаем данные о циклах
    cycles_data = get_all_cycles(access_token)
    if cycles_data:
        flat_cycles_data = flatten_cycles_data(cycles_data)
        write_to_google_sheets(flat_cycles_data, "cycles", [0])  # Пример уникального ключа - id

    update.message.reply_text("Данные успешно обновлены в Google Sheets!")

# Обработчик кнопки выбора листа
def handle_sheet_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Проверяем, что дата выбрана
    if selected_date is None:
        query.message.reply_text("Сначала введите дату с помощью команды /info.")
        return

    # Определяем, какой лист был выбран и предлагается выбор столбцов
    sheet_name = query.data
    context.user_data['sheet_name'] = sheet_name  # Сохраняем выбранный лист для последующего использования

    if sheet_name == "recovery":
        # Кнопки для листа "recovery"
        keyboard = [
            [InlineKeyboardButton("cycle id", callback_data='col_1'), InlineKeyboardButton("sleep id", callback_data='col_2'), InlineKeyboardButton("user id", callback_data='col_3')],
            [InlineKeyboardButton("created at", callback_data='col_4'), InlineKeyboardButton("updated at", callback_data='col_5'), InlineKeyboardButton("score state", callback_data='col_6')],
            [InlineKeyboardButton("user calibrating", callback_data='col_7'), InlineKeyboardButton("recovery score", callback_data='col_8'), InlineKeyboardButton("resting heart rate", callback_data='col_9')],
            [InlineKeyboardButton("hrv_rmssd_milli", callback_data='col_10'), InlineKeyboardButton("spo2_percentage", callback_data='col_11'), InlineKeyboardButton("skin_temp_celsius", callback_data='col_12')],
            [InlineKeyboardButton("Все данные", callback_data='all_data')]
        ]
    elif sheet_name == "workout":
        # Кнопки для листа "workout"
        keyboard = [
            [InlineKeyboardButton("id", callback_data='col_1'), InlineKeyboardButton("user id", callback_data='col_2'), InlineKeyboardButton("created at", callback_data='col_3')],
            [InlineKeyboardButton("updated at", callback_data='col_4'), InlineKeyboardButton("start", callback_data='col_5'), InlineKeyboardButton("end", callback_data='col_6')],
            [InlineKeyboardButton("timezone offset", callback_data='col_7'), InlineKeyboardButton("sport id", callback_data='col_8'), InlineKeyboardButton("sport name", callback_data='col_9')],
            [InlineKeyboardButton("score state", callback_data='col_10'), InlineKeyboardButton("strain", callback_data='col_11'), InlineKeyboardButton("average heart rate", callback_data='col_12')],
            [InlineKeyboardButton("max heart rate", callback_data='col_13'), InlineKeyboardButton("kilojoule", callback_data='col_14'), InlineKeyboardButton("percent recorded", callback_data='col_15')],
            [InlineKeyboardButton("distance meter", callback_data='col_16'), InlineKeyboardButton("altitude gain meter", callback_data='col_17'), InlineKeyboardButton("altitude change meter", callback_data='col_18')],
            [InlineKeyboardButton("zone zero milli", callback_data='col_19'), InlineKeyboardButton("zone one milli", callback_data='col_20'), InlineKeyboardButton("zone two milli", callback_data='col_21')],
            [InlineKeyboardButton("zone three milli", callback_data='col_22'), InlineKeyboardButton("zone four milli", callback_data='col_23'), InlineKeyboardButton("zone five milli", callback_data='col_24')],
            [InlineKeyboardButton("Все данные", callback_data='all_data')]
        ]
    elif sheet_name == "sleep":
        # Кнопки для листа "sleep"
        keyboard = [
            [InlineKeyboardButton("id", callback_data='col_1'), InlineKeyboardButton("user id", callback_data='col_2'), InlineKeyboardButton("created at", callback_data='col_3')],
            [InlineKeyboardButton("updated at", callback_data='col_4'), InlineKeyboardButton("start", callback_data='col_5'), InlineKeyboardButton("end", callback_data='col_6')],
            [InlineKeyboardButton("timezone offset", callback_data='col_7'), InlineKeyboardButton("nap", callback_data='col_8'), InlineKeyboardButton("score state", callback_data='col_9')],
            [InlineKeyboardButton("total in bed time milli", callback_data='col_10'), InlineKeyboardButton("total awake time milli", callback_data='col_11'), InlineKeyboardButton("total no data time milli", callback_data='col_12')],
            [InlineKeyboardButton("total light sleep time milli", callback_data='col_13'), InlineKeyboardButton("total slow wave sleep time milli", callback_data='col_14'), InlineKeyboardButton("total rem sleep time milli", callback_data='col_15')],
            [InlineKeyboardButton("sleep cycle count", callback_data='col_16'), InlineKeyboardButton("disturbance count", callback_data='col_17'), InlineKeyboardButton("baseline milli", callback_data='col_18')],
            [InlineKeyboardButton("need from sleep debt milli", callback_data='col_19'), InlineKeyboardButton("need from recent strain milli", callback_data='col_20'), InlineKeyboardButton("need from recent nap milli", callback_data='col_21')],
            [InlineKeyboardButton("respiratory rate", callback_data='col_22'), InlineKeyboardButton("sleep performance percentage", callback_data='col_23'), InlineKeyboardButton("sleep consistency percentage", callback_data='col_24')],
            [InlineKeyboardButton("sleep efficiency percentage", callback_data='col_25'), InlineKeyboardButton("Все данные", callback_data='all_data')]
        ]
    elif sheet_name == "cycles":
        # Кнопки для листа "cycles"
        keyboard = [
            [InlineKeyboardButton("id", callback_data='col_1'), InlineKeyboardButton("user id", callback_data='col_2'), InlineKeyboardButton("created at", callback_data='col_3')],
            [InlineKeyboardButton("updated at", callback_data='col_4'), InlineKeyboardButton("start", callback_data='col_5'), InlineKeyboardButton("end", callback_data='col_6')],
            [InlineKeyboardButton("timezone offset", callback_data='col_7'), InlineKeyboardButton("score state", callback_data='col_8'), InlineKeyboardButton("strain", callback_data='col_9')],
            [InlineKeyboardButton("kilojoule", callback_data='col_10'), InlineKeyboardButton("average heart rate", callback_data='col_11'), InlineKeyboardButton("max heart rate", callback_data='col_12')],
            [InlineKeyboardButton("Все данные", callback_data='all_data')]
        ]
    else:
        query.message.reply_text("Неизвестный лист.")
        return

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text("Выберите данные для вывода:", reply_markup=reply_markup)

def handle_column_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    column_choice = query.data  # Получаем выбор пользователя (столбец или все данные)
    sheet_name = context.user_data.get('sheet_name')  # Получаем выбранный лист

    if not sheet_name:
        query.message.reply_text("Ошибка: лист не выбран.")
        return

    # Авторизация и подключение к Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('whoop-439019-6c624110dac0.json', scope)
    client = gspread.authorize(creds)

    # Открытие выбранного листа
    spreadsheet = client.open("whoop")
    worksheet = spreadsheet.worksheet(sheet_name)

    # Получаем данные с листа
    data = worksheet.get_all_values()
    # Фильтрация данных по user_id и дате
    filtered_data = []
    telegram_id = query.from_user.id
    us_id = get_user_whoop_id(telegram_id)
    for row in data:
        if sheet_name == "recovery":
            if str(row[2]) == str(us_id) and str(row[3][:10]) == str(selected_date):
                filtered_data.append(row)
        else:
            if str(row[1]) == str(us_id) and str(row[2][:10]) == str(selected_date):
                filtered_data.append(row)

    # Обработка в зависимости от выбора пользователя
    response_text = ""
    if column_choice == 'all_data':
        response_text = f"Все данные с листа '{sheet_name}' для пользователя {us_id} на {selected_date}:\n"
        for row in filtered_data:
            response_text += ', '.join(row) + "\n"
    else:
        # Получаем номер столбца из выбора пользователя
        column_index = int(column_choice.split('_')[1]) - 1  # col_1 -> 0, col_2 -> 1 и т.д.
        response_text = f"Данные из столбца {column_index + 1} для пользователя {us_id} на {selected_date}:\n"
        for row in filtered_data:
            response_text += row[column_index] + "\n"

    if response_text:
        query.message.reply_text(response_text)
    else:
        query.message.reply_text(f"Нет данных для пользователя {user_id} на листе '{sheet_name}' за {selected_date}.")

# Обработчик команды /info для вывода кнопок
def info(update: Update, context: CallbackContext):
    global fl
    fl = 2
    update.message.reply_text("Введите дату (в формате ГГГГ-ММ-ДД):")
    return "WAITING_FOR_DATE"

# Обработчик текстовых сообщений для получения даты
def get_date(update: Update, context: CallbackContext):
    global fl
    if fl == 2:
        global selected_date
        selected_date = update.message.text.strip()  # Сохраняем введённую дату

        try:
            time.strptime(selected_date, "%Y-%m-%d")  # Проверка на правильность формата
        except ValueError:
            update.message.reply_text("Некорректный формат даты. Попробуйте снова в формате ГГГГ-ММ-ДД.")
            return

        # Показать кнопки выбора листа
        keyboard = [
            [InlineKeyboardButton("Recovery", callback_data='recovery'), InlineKeyboardButton("Workout", callback_data='workout')],
            [InlineKeyboardButton("Sleep", callback_data='sleep'), InlineKeyboardButton("Cycles", callback_data='cycles')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Выберите лист для получения данных:", reply_markup=reply_markup)
        return
    