import os
import re
from datetime import datetime

import requests
import telebot
from bs4 import BeautifulSoup as bs
from dotenv import load_dotenv
from telebot.apihelper import ApiTelegramException


load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode=None)
EDUCATION_PROGRAM_URL = 'http://znanie.vdnh.ru/?dates={}'
RE_DATE = r'^20[0-2][0-9].((0[1-9])|(1[0-2])).(0[1-9]|[1-2][0-9]|3[0-1])$'
RE_DATES_RANGE = r'^20[0-2][0-9].((0[1-9])|(1[0-2])).(0[1-9]|[1-2][0-9]|3[0-1])-' \
                 r'20[0-2][0-9].((0[1-9])|(1[0-2])).(0[1-9]|[1-2][0-9]|3[0-1])$'


def get_html(date):
    """Возвращает контент html-страницы с get-параметром dates"""
    url = EDUCATION_PROGRAM_URL.format(date)
    try:
        response = requests.get(url, timeout=30)
        # лог для Heroku
        print('The response is received successfully')
        return response.content
    except requests.Timeout:
        # лог для Heroku
        print('TIMEOUT ERROR')
    except requests.RequestException:
        # лог для Heroku
        print(f'The request failed at the address: {url}')
    # возвращаем дефолтное валидное значение при неудавшемся запросе
    return b''


def parse_events(response):
    """Возвращает в отформатированном виде ответ пользователю с мероприятиями"""
    events = []
    answer = ''
    html = bs(response, 'html.parser')
    event_items = html.find_all('div', class_='event')
    # выбираем нужные элементы на странице
    for event in event_items:
        events.append({
            'place': event.find('div', class_='place').text.lstrip(),
            'title': event.find('div', class_='title').text.strip(),
            'date': event.find('div', class_='fulldate').find_all('div')[0].text.strip(),
            'time': event.find('div', class_='fulldate').find_all('div')[1].text.strip(),
        })
    # проходимся по элементам
    for event in events:
        # делаем проверку на площадку, так как не все нас интересуют
        if event['place'].strip() in (
                'Дом ремесел (павильон №47)',
                'Павильон «Рабочий и колхозница»',
                'Летний кинотеатр-лекторий',
                'Крыша павильона «Рабочий и колхозница»'
        ):
            # и добавляем элемент в ответ
            answer += f'<b>Площадка:</b>\n{event["place"]}\n' \
                      f'<b>Описание:</b>\n{event["title"]}\n' \
                      f'<b>Дата:</b>\n{event["date"]}\n' \
                      f'<b>Время начала:</b>\n{event["time"]}\n\n'
    return answer


@bot.message_handler(commands=['start'])
def greeting(message):
    """Приветствие при команде /start"""
    with open('stickers/AnimatedSticker.tgs', 'rb') as sticker:
        bot.send_sticker(message.chat.id, sticker)
    bot.send_message(message.chat.id, text=f'Привет, {message.from_user.first_name}!\n\n'
                                           f'Узнайте, как мной пользоваться /help.')


@bot.message_handler(commands=['help'])
def show_help_text(message):
    """Показывает подсказку по использованию бота при команде /help"""
    bot.send_message(message.chat.id,
                     text='Отправьте дату в формате YYYY.MM.DD, чтобы увидеть мероприятия в этот день.\n\n'
                          'Отправьте диапозон дат в формате YYYY.MM.DD-YYYY.MM.DD, '
                          'чтобы увидеть мероприятия в эти дни.\n\n'
                          'Команда /today показывает сегодняшние мероприятия.')


@bot.message_handler(commands=['today'])
def show_today_events(message):
    today = datetime.today().strftime('%Y.%m.%d')
    try:
        bot.send_message(message.chat.id, parse_events(get_html(today)), parse_mode='html')
    except ApiTelegramException:
        bot.send_message(message.chat.id, f'На {today} не нашлось мероприятий')


@bot.message_handler(content_types=['text'])
def show_events_by_date(message):
    """Формирует ответ пользователю"""
    if re.search(RE_DATE, message.text) or re.search(RE_DATES_RANGE, message.text):
        try:
            bot.send_message(message.chat.id, parse_events(get_html(message.text)), parse_mode='html')
        except ApiTelegramException:
            bot.send_message(message.chat.id, f'На {message.text} не нашлось мероприятий')
    else:
        bot.send_message(message.chat.id, f'Неверный формат даты')


if __name__ == '__main__':
    # лог для Heroku
    print('ALL OK')
    bot.polling(none_stop=True)
