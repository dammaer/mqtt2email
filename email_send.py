import smtplib
import socket
from email.headerregistry import Address
from email.message import EmailMessage
from configparser import ConfigParser

config = ConfigParser()
config.read('settings.ini')

SMTP_SERVER = config.get('email', 'SMTP_SERVER')
SMTP_PORT = config.get('email', 'SMTP_PORT')
SMTP_LOGIN = config.get('email', 'SMTP_LOGIN')
SMTP_PASSWD = config.get('email', 'SMTP_PASSWD')

EMAIL_DISP_NAME = config.get('email', 'EMAIL_DISP_NAME')
EMAIL_USERNAME = config.get('email', 'EMAIL_USERNAME')
EMAIL_DOMAIN = config.get('email', 'EMAIL_DOMAIN')


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
    msg = EmailMessage()
    msg['Subject'] = 'Показания счётчиков ООО "LanTa"'
    msg['From'] = Address(EMAIL_DISP_NAME, EMAIL_USERNAME, EMAIL_DOMAIN)
    msg['To'] = (Address(addr_spec=msg_to),)
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
    data = ({'address': 'test', 'model': 1234, 'serial': 12345, 'energy': '1001'},
            {'address': 'test2', 'model': 4321, 'serial': 12345, 'energy': '2002'})
    email_send('login@domain.com', data)
