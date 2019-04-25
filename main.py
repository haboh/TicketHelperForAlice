'''
Данная программа позволяет делать следующие типы запросов:
Самый дешевый билет от A до B на сегодня
Цена самого дешевого билета от A до B на этот месяц
Дешевый билет без / с одной / с двумя пересадками от A до B
Самые популярные рейсы из A
'''

import requests
import json
import datetime
from flask import Flask, request
import logging
from config import TOKEN

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, filename='app.log',
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
# Создаем Flask приложение
app = Flask(__name__)


class TicketsFinder:
    # Загружаем список кодов и имен городов со всеми падежами
    # и список кодов и имен авиакомпаний
    def __init__(self):
        # Делаем запрос к api
        # Вернет json файл со списком всех кородов, их кодов,
        # а также падежей
        cities = requests.get(
            'http://api.travelpayouts.com/data/ru/cities.json'
        )

        # Список со всеми городами и их всевозможными падежами
        self.cities_list = []
        # Словарь с ключом - именем города и значением кодом города
        self.cities_dict = {}
        # Словарь обратный вышеописанному
        self.codes_cities_dict = {}
        # Словарь с родительными падежами в зависимости от кода города
        self.ro_cities = {}

        # Строим все вышеописанные массивы и словари
        for city in cities.json():
            city_name = city['name']
            if city_name is None:
                continue
            city_code = city['code']
            city_name_lower = city['name'].lower()

            # Добавляем основные коды и имена в словари и список
            if type(city_name) == str:
                self.codes_cities_dict[city_code] = city_name
                self.cities_list.append(city_name_lower)
                self.cities_dict[city_name_lower] = city_code

            # Добавляем падежи
            if 'cases' in city:
                for name in city['cases'].values():
                    self.cities_dict[name.lower()] = city_code
                    self.cities_list.append(name.lower())

                # Добавляем родительный падеж
                # если не находим, то именительный по умолчанию
                if 'ro' in city['cases']:
                    self.ro_cities[city_code] = city['cases']['ro']
                else:
                    self.ro_cities[city_code] = city_name

        # Делаем аналогично, как с городами,
        # только без падежей
        airlines = requests.get(
            'http://api.travelpayouts.com/data/ru/airlines.json'
        )

        # Словарь с ключом - кодом авиакомпании
        # и значением ее названием
        self.airlines = {}
        for airline in airlines.json():
            self.airlines[airline['code']] = airline['name']

    # Метод позволяет найти код города по любому из доступных падежей
    def find_city_iata_code(self, city):
        city_lower = city.lower()
        if city_lower in self.cities_dict:
            return self.cities_dict[city_lower]

    # Метод позволяет найти название авиакомпании по ее коду
    def find_airline_name(self, iata_code):
        if iata_code in self.airlines:
            return self.airlines[iata_code]

    # Метод позволяет найти название города по его коду
    def get_city_by_code(self, code):
        if code in self.codes_cities_dict:
            return self.codes_cities_dict[code]

    # Метод позволяет найти лучший билет из точки A
    # в точку B на сегодня
    def find_best_ticket_for_today(self, origin, destination):
        # Код города отправления
        city_from = self.find_city_iata_code(origin)
        # Код города прибытия
        city_to = self.find_city_iata_code(destination)

        # Если города отправления или прибытия
        # нет в списке, то ничего не возвращаем
        if city_to is None or city_from is None:
            return

        # Берем текущую дату и приводим ее к виду YYYY-MM-DD
        now = datetime.datetime.now()
        cur_date = '-'.join(map(lambda x: str(x) if x > 9 else '0' + str(x),
                                [now.year, now.month, now.day]))

        # Формируем параметры запроса
        params = {
            'token': TOKEN,
            'origin': city_from,
            'destination': city_to,
            'depart_date': cur_date,
        }

        # Делаем запрос к api
        response = requests.get(
            'http://api.travelpayouts.com/v1/prices/calendar',
            params=params
        )

        logging.info('http://api.travelpayouts.com/v1/prices/calendar')
        logging.info(params)

        # Если нам не ответили или ответ не успешен,
        # то ничего не возвращаем
        if not response:
            return
        response_json = response.json()
        if response_json['success']:
            # Список дат в словаре, первая - самый дешевый билет
            dates = list(response_json['data'].keys())

            # Если список пустой значит рейсов нет
            if not dates:
                return None
            return response_json['data'][dates[0]]

    # Метод позволяет искать среди токенов,
    # полученых в запросе, города, находящиеся в базе
    def find_cities(self, tokens):
        cities = []
        for word in tokens:
            word_lower = word.lower()
            if word_lower in self.cities_list:
                cities.append(word_lower)
        return cities

    # Метод позволяет найти лучшие билеты и пункта A
    # в пункт B в течении месяца от текущего дня
    def find_tickets_for_a_month(self, origin, destination):
        # Код города отправления
        city_from = self.find_city_iata_code(origin)
        # Код города прибытия
        city_to = self.find_city_iata_code(destination)
        # Если какой-то из городов не в нашей базе,
        # то ничего не возвращаем
        if city_to is None or city_from is None:
            return

        # Узнаем текущую дату в формате YYYY-MM-DD
        now = datetime.datetime.now()
        cur_date = '-'.join(map(lambda x: str(x) if x > 9 else '0' + str(x),
                                [now.year, now.month, now.day]))

        # Формируем данные запроса
        params = {
            'token': TOKEN,
            'origin': city_from,
            'destination': city_to,
            'month': cur_date,
        }

        # Делаем запрос
        response = requests.get(
            'http://api.travelpayouts.com/v2/prices/month-matrix',
            params=params,
        )

        logging.info('http://api.travelpayouts.com/v2/prices/month-matrix')
        logging.info(params)

        # Если запрос не удачный, то завершаем метод
        if not response:
            return
        response_json = response.json()

        # Если запрос успешен, то возвращаем ответ
        if response_json['success']:
            return response_json['data']

    # Позволяет получить родительный падеж города
    def get_ro(self, city):
        city_lower = city.lower()
        code = self.find_city_iata_code(city_lower)
        return self.ro_cities[code]

    # Возвращает список популярных направлений,
    # из какого-то города
    def find_popular_tickets(self, origin):
        # Проверяем город на корректность
        city_from = self.find_city_iata_code(origin)
        if city_from is None:
            return

        # Формируем параметры запроса к api
        params = {
            'origin': city_from,
            'token': TOKEN,
        }

        # Делаем запрос
        response = requests.get(
            'http://api.travelpayouts.com/v1/city-directions',
            params=params
        )

        logging.info('http://api.travelpayouts.com/v1/city-directions')
        logging.info(params)

        # Проверяем запрос на успешность
        if not response:
            return
        response_json = response.json()

        # Если запрос успешен, то возвращаем все варианты
        if response_json['success']:
            return response_json['data']

    def find_best_ticket(self, origin, destination):
        # Код города отправления
        city_from = self.find_city_iata_code(origin)
        # Код города прибытия
        city_to = self.find_city_iata_code(destination)
        # Если какой-то из городов не в нашей базе,
        # то ничего не возвращаем
        if city_to is None or city_from is None:
            return

        # Формируем данные запроса
        params = {
            'token': TOKEN,
            'origin': city_from,
            'destination': city_to,
        }

        # Делаем запрос
        response = requests.get(
            'http://api.travelpayouts.com/v1/prices/cheap',
            params=params,
        )

        logging.info('http://api.travelpayouts.com/v1/prices/cheap')
        logging.info(params)

        # Если запрос не удачный, то завершаем метод
        if not response:
            return
        response_json = response.json()

        # Если запрос успешен, то возвращаем ответ
        if response_json['success']:
            return response_json['data'][city_to]


# То что будет нам все искать
tickets_finder = TicketsFinder()


@app.route('/post', methods=['POST'])
def main():
    # Логируем запрос
    logging.info('Request: %r', request.json)

    # Готовим ответ
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)

    # Логируем ответ
    logging.info('Request: %r', response)

    return json.dumps(response)


def handle_dialog(res, req):
    #  Если пользователь новый, то посылаем ему справку
    if req['session']['new'] or not req['request']['command']:
        res['response']['text'] \
            = 'Привет, я могу помочь с подбором рейса.'
        return

    # Преобразуем токены к нижнему регистру
    tokens = [token.lower() for token in req['request']['nlu']['tokens']]

    # Ищем среди токенов названия городов
    cities = tickets_finder.find_cities(tokens)

    # На всякий случай непредвиденных обстоятельств
    try:
        # Если количество городов 2, это значит,
        # что пользователь хочет билет между двумя городами
        if len(cities) == 2:
            # Пункт отправления
            origin = cities[0].capitalize()
            # Пункт назначения
            destination = cities[1].capitalize()

            # Ищем самый дешевый билет на следующий месяц
            if ('дешевый' in tokens or 'дешевого' in tokens) and 'месяц' in tokens:
                # Получаем список всех билетов на месяц
                flights = tickets_finder.find_tickets_for_a_month(
                    origin,
                    destination,
                )

                # Если билетов нет, то ошибка
                if not flights:
                    res['response']['text'] = 'Авиарейс не найден.'
                    return

                # Берем первый как самый дешевый
                price = flights[0]['value']
                # И сравниваем со всеми остальные по стоимости
                for flight in flights:
                    price = min(price, flight['value'])

                # Формируем ответ
                res['response']['text'] = \
                    'Самый дешевый билет от {} до {} на этот месяц:\n'.format(
                        tickets_finder.get_ro(origin),
                        tickets_finder.get_ro(destination)
                    )
                res['response']['text'] += str(price) + ' рублей'

            # Ищем самый дешевый
            elif 'дешевый' in tokens \
                    and ('пересадок' in tokens or 'пересадки' in tokens
                         or 'пересадками' in tokens or 'пересадкой' in tokens):
                # Делаем запрос к api о самых дешевых с пересадками и
                # без пересадок
                flights = tickets_finder.find_best_ticket(origin, destination)
                # Без пересадок
                if 'без' in tokens:
                    changes = 0
                    flight = flights['0']

                # С одной пересаткой
                elif 'одной' in tokens or '1' in tokens or 'одна' in tokens:
                    changes = 1
                    flight = flights['1']

                # С двумя пересадками
                else:
                    changes = 2
                    flight = flights['2']

                # Готовим информация
                flight_number = flight['airline'] + str(flight['flight_number'])
                airline_name = tickets_finder.find_airline_name(flight['airline'])
                flight_price = str(flight['price'])
                departure_time = flight['departure_at'][11:-1]
                departure_date = flight['departure_at'][:10]

                # Формируем текст ответа
                text = 'Билет от {} до {}:\n' + 'Номер - {}\n' \
                       + 'Дата вылета - {}\n' + \
                       'Время вылета - {}\n' + \
                       'Авиакомпания - {}\n' + \
                       'Цена - {} рублей\n' + \
                       'Количество пересадок - {}'

                text = text.format(
                    origin,
                    destination,
                    flight_number,
                    departure_date,
                    departure_time,
                    airline_name,
                    flight_price,
                    changes,
                )

                # Готовим ответ
                res['response']['text'] = text
                res['response']['buttons'] = [
                    {
                        "title": flight_number,
                        "payload": {},
                        "url": "https://yandex.ru/search/?text={}".format(
                            flight_number
                        ),
                        "hide": True,
                    }
                ]

            # Иначе думаем, что нам нужно самый дешевый билет на сегодня
            else:
                # Ищем лучший билет на сегодня
                flight = tickets_finder.find_best_ticket_for_today(
                    origin,
                    destination,
                )

                # По умолчанию авиарейс не найден
                text = 'Авиарейс не найден.'
                if flight is not None:
                    # Формируем ответ
                    flight_name = flight['airline'] + str(flight['flight_number'])
                    departure_time = flight['departure_at'][11:-1]
                    departure_date = flight['departure_at'][:10]

                    text = 'Билет от {} до {} на сегодня:\n' + 'Номер - {}\n' \
                           + 'Дата вылета - {}\n' + \
                           'Время вылета - {}\n' + \
                           'Авиакомпания - {}\n' + \
                           'Цена - {} рублей'
                    text = text.format(
                        tickets_finder.get_ro(origin),
                        tickets_finder.get_ro(destination),
                        flight_name,
                        departure_date,
                        departure_time,
                        tickets_finder.find_airline_name(
                            flight['airline']
                        ),
                        str(flight['price']),
                    )

                    # Добавляем кнопку для поиска билета в яндексе
                    res['response']['buttons'] = [
                        {
                            "title": flight_name,
                            "payload": {},
                            "url": "https://yandex.ru/search/?text={}".format(
                                flight_name
                            ),
                            "hide": True,
                        }
                    ]

                # Ответ - получившийся текст
                res['response']['text'] = text

        # А если 1, то значит только из одного города
        elif len(cities) == 1:
            origin = cities[0].capitalize()
            if 'популярные' in tokens or 'популярных' in tokens:
                # Получаем список самых популярных
                popular = tickets_finder.find_popular_tickets(origin)

                # Формируем ответ
                res['response']['text'] = \
                    'Самые популярные авиарейсы из ' + \
                    tickets_finder.get_ro(origin.lower()) + ':\n'
                res['response']['buttons'] = []

                # Добавляем все доступные рейсы
                for city, info in list(popular.items()):
                    # Номер рейса
                    flight_number = info['airline'] + str(info['flight_number'])
                    # Название авиакомпании
                    airline = tickets_finder.find_airline_name(info['airline'])

                    if flight_number is not None and airline is not None:
                        # Добавляем текст с названием рейса и авиакомпании
                        res['response']['text'] += \
                            flight_number + ' - ' \
                            + tickets_finder.get_city_by_code(
                                city).capitalize() \
                            + ' - ' + airline + '\n'

                        # Добавляем кнопку с поиском рейса в яндексе
                        res['response']['buttons'].append(
                            {
                                "title": flight_number,
                                "payload": {},
                                "url": "https://yandex.ru/search/?text={}".format(
                                    flight_number
                                ),
                                "hide": True,
                            }
                        )
            # В противном случае команды ме не знаем
            else:
                res['response']['text'] = 'Я не знаю такой команды.'

        # В противном случае команды ме не знаем
        else:
            res['response']['text'] = 'Я не знаю такой команды.'

    # Если вдруг что-то случилось не по плану,
    # скорее всего рейсов просто не нашлось
    except Exception as e:
        res['response']['text'] = 'Я не знаю, что случилось. Возможно таких рейсов просто не существует.'

        # Прологируем для анализа
        logging.error(e)


if __name__ == '__main__':
    app.run()
