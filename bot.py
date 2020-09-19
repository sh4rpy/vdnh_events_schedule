import os
import re

import requests
import telebot
from bs4 import BeautifulSoup as bs
from dotenv import load_dotenv
from telebot.apihelper import ApiTelegramException


load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode=None)
EDUCATION_PROGRAM_URL = 'http://znanie.vdnh.ru/?dates={}'
RE_DATE = r'^20[0-2][0-9].((0[1-9])|(1[0-2])).([0-2][1-9]|3[0-1])$'


def get_html(date):
    """Возвращает контент html-страницы с get-параметром date"""
    try:
        response = requests.get(EDUCATION_PROGRAM_URL.format(date), timeout=30)
    except requests.Timeout:
        # лог для Heroku
        print('TIMEOUT ERROR')
    else:
        # лог для Heroku
        print('The response is received successfully')
        return response.content


def parse_events(response):
    """Возвращает в отформатированном виде ответ пользователю с мероприятиями"""
    events = []
    answer = ''
    html = bs(response, 'html.parser')
    event_items = html.find_all('div', class_='event')
    for event in event_items:
        events.append({
            'place': event.find('div', class_='place').text.lstrip(),
            'title': event.find('div', class_='title').text.strip(),
            'date': event.find('div', class_='fulldate').find_all('div')[0].text.strip(),
            'time': event.find('div', class_='fulldate').find_all('div')[1].text.strip(),
        })
    for event in events:
        # делаем проверку на площадку, так как не все нас интересуют
        if event['place'].strip() in (
                'Дом ремесел (павильон №47)',
                'Павильон «Рабочий и колхозница»',
                'Летний кинотеатр-лекторий',
                'Крыша павильона «Рабочий и колхозница»'
        ):
            answer += f'<b>Площадка:</b>\n{event["place"]}\n' \
                      f'<b>Описание:</b>\n{event["title"]}\n' \
                      f'<b>Дата:</b>\n{event["date"]}\n' \
                      f'<b>Время начала:</b>\n{event["time"]}\n\n'
    return answer


@bot.message_handler(commands=['start', 'help'])
def greeting(message):
    """Команды /start и /help"""
    if message.text == '/start':
        with open('stickers/AnimatedSticker.tgs', 'rb') as sticker:
            bot.send_sticker(message.chat.id, sticker)
        bot.send_message(message.chat.id, text=f'Привет, {message.from_user.first_name}!')

    else:
        bot.send_message(message.chat.id,
                         text='Отправьте дату в формате YYYY.MM.DD, чтобы увидеть мероприятия в этот день.')


@bot.message_handler(content_types=['text'])
def show_events(message):
    """Формирует ответ пользователю"""
    if re.search(RE_DATE, message.text):
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
