import smtplib
import socket
import os
from email.headerregistry import Address
from email.message import EmailMessage
from configparser import ConfigParser

ini = ConfigParser()
ini.read(os.path.dirname(os.path.abspath(__file__)) + '/settings.ini')

SMTP_SERVER = ini.get('email', 'SMTP_SERVER')
SMTP_PORT = ini.get('email', 'SMTP_PORT')
SMTP_LOGIN = ini.get('email', 'SMTP_LOGIN')
SMTP_PASSWD = ini.get('email', 'SMTP_PASSWD')

EMAIL_DISP_NAME = ini.get('email', 'EMAIL_DISP_NAME')
EMAIL_USERNAME = ini.get('email', 'EMAIL_USERNAME')
EMAIL_DOMAIN = ini.get('email', 'EMAIL_DOMAIN')
EMAIL_COPY = [Address(addr_spec=addr)
              for addr in ini.get(
                  'email', 'EMAIL_COPY', fallback='').split()]


class EmailSendIsFail(Exception):
    pass


def create_text_msg(data):
    text = '| Адрес | Модель | Серийный номер | Показания |\n'
    for d in data:
        text += (f"| {d['address']} | {d['model']} | "
                 f"{d['serial']} | {d['energy']} |\n")
    return text


def create_html_msg(data):
    tr = ''
    for d in data:
        tr += """
            <tr>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
            </tr>""".format(d['address'], d['model'], d['serial'], d['energy'])
    msg = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Таблица со счетчиками</title>
</head>
<body>
    <table border="1">
        <thead>
            <tr>
                <th>Адрес</th>
                <th>Модель</th>
                <th>Серийный номер</th>
                <th>Показания</th>
            </tr>
        </thead>
        <tbody>{}
        </tbody>
    </table>
</body>
</html>
""".format(tr)
    return msg


def email_send(msg_to, data):
    data.sort(key=lambda k: k['address'])
    msg = EmailMessage()
    msg['Subject'] = 'Показания счётчиков ООО "LanTa"'
    msg['From'] = Address(EMAIL_DISP_NAME, EMAIL_USERNAME, EMAIL_DOMAIN)
    msg['To'] = (Address(addr_spec=msg_to),)
    msg['Bcc'] = EMAIL_COPY
    msg.set_content(create_text_msg(data))
    msg.add_alternative(create_html_msg(data), subtype='html')
    try:
        with smtplib.SMTP(SMTP_SERVER, port=SMTP_PORT) as s:
            s.login(SMTP_LOGIN, SMTP_PASSWD)
            s.send_message(msg)
    except (socket.gaierror, smtplib.SMTPAuthenticationError,
            ConnectionRefusedError) as e:
        raise EmailSendIsFail(f"Проблемы с отправкой email: {e}")


if __name__ == "__main__":
    data = ({'address': 'test', 'model': 1234,
             'serial': 12345, 'energy': '1001'},
            {'address': 'test2', 'model': 4321,
             'serial': 12345, 'energy': '2002'})
    # email_send('login@domain.com', data)
