import logging
import os
import socket
import time
import urllib.parse
import urllib.request
from configparser import ConfigParser
from datetime import datetime
from json import dump as json_dump
from json import load as json_load

import paho.mqtt.client as mqtt

from email_send import EmailSendIsFail, email_send

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


def file_path(filename):
    return os.path.join(BASE_PATH, filename)


ini = ConfigParser()
ini.read(file_path('settings.ini'))

CONFIG = file_path('config.json')

BROKER = ini.get('broker', 'BROKER')
BROKER_LOGIN = ini.get('broker', 'BROKER_LOGIN')
BROKER_PASSWD = ini.get('broker', 'BROKER_PASSWD')

TG_CHAT_IDS = ini.get('telegram', 'TG_CHAT_IDS').split()
TG_TOKEN = ini.get('telegram', 'TG_TOKEN')


class BrokerIsFail(Exception):
    pass


class EmptyTopicList(Exception):
    pass


def load_config():
    with open(CONFIG, 'r') as f:
        return json_load(f)


def save_config(config):
    with open(CONFIG, 'w', encoding="utf-8") as f:
        json_dump(config, f, ensure_ascii=False,
                  indent=4, separators=(',', ': '))


def setup_logging(log_file=file_path('log')):
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')

    logger = logging.getLogger('my_logger')
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def tg_send(msg):
    tg_msg = ('Скрипт отправки показаний счётчиков.\n\U000026A0 '
              f'Есть проблема: {msg}')
    for chat_id in TG_CHAT_IDS:
        params = {
            'chat_id': chat_id,
            'text': tg_msg,
        }
        url = (f"https://api.telegram.org/bot{TG_TOKEN}/"
               f"sendMessage?{urllib.parse.urlencode(params)}")
        try:
            with urllib.request.urlopen(url) as response:
                response.read().decode('utf-8')
        except Exception as e:
            print(f"Error sending message to Telegram: {e}")
        time.sleep(1)


def get_broker_data(topics: list[tuple[str, int]]) -> dict:
    def on_message(client, userdata, message):
        userdata.append(message)
        if len(userdata) == 1:
            client.unsubscribe(message.topic)
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqttc.on_message = on_message
    mqttc.user_data_set([])
    mqttc.username_pw_set(BROKER_LOGIN, BROKER_PASSWD)
    try:
        mqttc.connect(BROKER)
        mqttc.subscribe(topics)
        mqttc.loop_start()
        time.sleep(1)
        mqttc.loop_stop()
        merged_dict = {msg.topic: msg.payload.decode("utf-8")
                       for msg in mqttc.user_data_get()}
        return merged_dict
    except socket.gaierror:
        raise BrokerIsFail('Брокер недоступен!')
    except ValueError:
        raise EmptyTopicList


def check_send_time_and_status(datetime_expression, email_sent) -> bool:
    minute, hour, day, month = datetime_expression.split()
    curr_dt = datetime.now().replace(microsecond=0, second=0)
    spec_dt = datetime(
        year=datetime.now().year,
        month=int(month) if month.isdigit() else datetime.now().month,
        day=int(day) if day.isdigit() else datetime.now().day,
        hour=int(hour) if hour.isdigit() else datetime.now().hour,
        minute=int(minute) if minute.isdigit() else datetime.now().minute,
        second=0,
        microsecond=0
    )
    if email_sent == 0 and curr_dt >= spec_dt:
        return True
    elif email_sent == 1 and spec_dt > curr_dt:
        return False
    return None


def list_of_topics(nodes, topic) -> list:
    return [(device[topic], 0)
            for item in nodes
            for device in item['device']
            ]


def main():
    config, changed = load_config(), False
    logger = setup_logging()
    for index, company in enumerate(config['company']):
        for date, state in company['date'].items():
            check = check_send_time_and_status(date, state)
            if check is True:
                nodes = [node for node in config['node']
                         if node['company'] == company['name']]
                serial_energy_list = list_of_topics(
                    nodes, 'serial') + list_of_topics(nodes, 'energy')
                try:
                    broker_data = get_broker_data(serial_energy_list)
                    result = [{'address': item['address'],
                               'model': device['model'],
                               'serial': broker_data[device['serial']],
                               'energy': broker_data[device['energy']]}
                              for item in nodes
                              for device in item['device']]
                    email_send(company['email'], result)
                    config['company'][index]['date'][date] = 1
                    changed = True
                    logger.info('Показания успешно отправлены '
                                f"{company['name']}")
                except (BrokerIsFail, EmailSendIsFail) as e:
                    tg_send(e)
                    logger.critical(e)
                    return
                except KeyError as e:
                    msg = f'Нет данных от топика указанного в конфиге: {e}'
                    tg_send(msg)
                    logger.error(msg)
                except EmptyTopicList:
                    msg = ("Нет связанных узлов в конфиге для"
                           f" {company['name']}")
                    logger.warning(msg)
            elif check is False:
                config['company'][index]['date'][date] = 0
                changed = True
    save_config(config) if changed else None


if __name__ == "__main__":
    main()
