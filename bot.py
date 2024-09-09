import re
import logging
import traceback
from time import sleep
import os

import psycopg2
from dotenv import load_dotenv

from telegram import Update, ForceReply
from telegram import ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, StringRegexHandler
import paramiko

load_dotenv()
TOKEN = os.getenv('TOKEN')

RM_HOST = os.getenv("RM_HOST")
RM_PORT = int(os.getenv("RM_PORT"))
RM_USER = os.getenv("RM_USER")
RM_PASSWORD = os.getenv("RM_PASSWORD")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DATABASE = os.getenv("DB_DATABASE")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)

logging.basicConfig(
    filename='/home/logs.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)
logger.warning("START")


class DatabaseConnection:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=DB_DATABASE,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()


def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f"Привет, {user.full_name}!")


def find_phone_number_command(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'find_phone_number'


def find_email_command(update: Update, context):
    update.message.reply_text('Введите текст для поиска email-адресов: ')

    return 'find_email'


def verify_password_command(update: Update, context):
    update.message.reply_text('Введите пароль: ')

    return 'verify_password'


def find_phone_number(update: Update, context):
    logger.info("find_phone_number started")
    try:
        user_input = update.message.text
        phone_mum_regex = re.compile(r"(8|\+7)([( -]*\d{3}[) -]*\d{3}[ -]*\d{2}[ -]*\d{2})")
        phone_number_list = phone_mum_regex.findall(user_input)

        if not phone_number_list:
            update.message.reply_text("Телефонные номера не найдены")
            logger.info("There is no numbers")
            return

        phone_numbers = ""
        for i, phone_tuple in enumerate(phone_number_list):
            phone_numbers += f"{i + 1}. {''.join(phone_tuple)}\n"

        update.message.reply_text(phone_numbers)
        logger.info("Found:", phone_numbers.replace("\n", "\\n"))
        context.user_data['phones'] = [i[0] + i[1] for i in phone_number_list]

        update.message.reply_text("Сохранить? Да/Нет")
        return 'save_phones'
    except Exception as e:
        logger.error(f"Error: {e}")

    return ConversationHandler.END


def save_phone_numbers(update: Update, context):
    try:
        user_input = update.message.text
        if user_input == "Да":
            if emails := context.user_data['phones']:
                with DatabaseConnection() as conn:
                    with conn.cursor() as cur:
                        for email in emails:
                            cur.execute("INSERT INTO phones (phone_number) VALUES (%s)", (email,))
                    conn.commit()
                update.message.reply_text('Телефонные номера добавлены в базу данных')
        return ConversationHandler.END
    except Exception as e:
        update.message.reply_text("Ошибка при добавлении телефонных номеров")
        logger.error(f"Error: {e}")


def find_email(update: Update, context):
    logger.info("find_email started")
    try:
        user_input = update.message.text
        email_regex = re.compile(r"[\.\-\w]+@\w+\.\w+")
        email_list = email_regex.findall(user_input)

        if not email_list:
            update.message.reply_text("Email-адреса не найдены")
            logger.info("There is no emails")
            return ConversationHandler.END

        email_addresses = ""
        for i, email_tuple in enumerate(email_list):
            email_addresses += f"{i + 1}. {''.join(email_tuple)}\n"

        update.message.reply_text(email_addresses)
        logger.info("Found:", email_addresses.replace("\n", "\\n"))
        context.user_data['emails'] = email_list

        update.message.reply_text("Сохранить? Да/Нет")
        return 'save_email'
    except Exception as e:
        logger.error(f"Error: {e}")

    return ConversationHandler.END


def save_email(update: Update, context):
    try:
        user_input = update.message.text
        if user_input == "Да":
            if emails := context.user_data['emails']:
                with DatabaseConnection() as conn:
                    with conn.cursor() as cur:
                        for email in emails:
                            cur.execute("INSERT INTO emails (email) VALUES (%s)", (email,))
                    conn.commit()
                update.message.reply_text('Email адреса добавлены в базу данных')
        return ConversationHandler.END
    except Exception as e:
        update.message.reply_text("Ошибка при добавлении email адресов")
        logger.error(f"Error: {e}")


def verify_password(update: Update, context):
    logger.info("verify_password started")
    try:
        user_input = update.message.text

        if any([
            len(user_input) < 8,
            re.search(r"[A-Z]", user_input) is None,
            re.search(r"[a-z]", user_input) is None,
            re.search(r"[0-9]", user_input) is None,
            re.search(r"[!@#$%^&*()]", user_input) is None
        ]):
            update.message.reply_text("Пароль простой")
        else:
            update.message.reply_text("Пароль сложный")

        logger.info("verify_password OK")
    except Exception as e:
        logger.error(f"Error: {e}")

    return ConversationHandler.END


def get_release(update: Update, context):
    logger.info("get_release started")
    try:
        stdin, stdout, stderr = client.exec_command('uname -r')
        data = stdout.read() + stderr.read()

        update.message.reply_text(data.decode())

        logger.info("get_release OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_uname(update: Update, context):
    logger.info("get_uname started")
    try:
        stdin, stdout, stderr = client.exec_command('uname -p')
        text = f"Тип процессора: " + (stdout.read() + stderr.read()).decode()
        stdin, stdout, stderr = client.exec_command('uname -n')
        text += f"Имя хоста: " + (stdout.read() + stderr.read()).decode()
        stdin, stdout, stderr = client.exec_command('uname -v')
        text += f"Версия ядра: " + (stdout.read() + stderr.read()).decode()

        update.message.reply_text(text)
        logger.info("get_uname OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_uptime(update: Update, context):
    logger.info("get_uptime started")
    try:
        stdin, stdout, stderr = client.exec_command('uptime -p')
        text = f"Время работы: " + (stdout.read() + stderr.read()).decode()[3:]

        update.message.reply_text(text)
        logger.info("get_uptime OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_df(update: Update, context):
    logger.info("get_df started")
    try:
        stdin, stdout, stderr = client.exec_command('df -h')
        text = "*Состояние файловой системы:*\n```\n" + (stdout.read() + stderr.read()).decode() + "\n```"

        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info("get_df OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_free(update: Update, context):
    logger.info("get_df started")
    try:
        stdin, stdout, stderr = client.exec_command('free -m')
        text = "*Состояние оперативной памяти \(в мегабайтах\):*\n```\n" + (
                stdout.read() + stderr.read()).decode() + "\n```"

        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info("get_free OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_mpstat(update: Update, context):
    logger.info("get_mpstat started")
    try:
        stdin, stdout, stderr = client.exec_command('mpstat -A')
        text = "*Производительность системы:*\n```\n" + (stdout.read() + stderr.read()).decode() + "\n```"

        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info("get_mpstat OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_w(update: Update, context):
    logger.info("get_w started")
    try:
        stdin, stdout, stderr = client.exec_command('who')
        text = "*Пользователи:*\n```\n" + (stdout.read() + stderr.read()).decode() + "\n```"

        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info("get_w OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_auths(update: Update, context):
    logger.info("get_auths started")
    try:
        stdin, stdout, stderr = client.exec_command('last')
        text = (stdout.read() + stderr.read()).decode()

        logs = list()

        for i in text.split("\n"):
            if "reboot" not in i:
                logs.append(i)
                if len(logs) == 10:
                    break

        update.message.reply_text("<b>Последние 10 входов в систему:</b>\n<pre>" + "\n".join(logs) + "\n</pre>",
                                  parse_mode=ParseMode.HTML)
        logger.info("get_auths OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_critical(update: Update, context):
    logger.info("get_critical started")
    try:
        stdin, stdout, stderr = client.exec_command('journalctl --priority=crit | tail -n 5')
        text = (stdout.read() + stderr.read()).decode()

        update.message.reply_text(text)
        logger.info("get_critical OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_ps(update: Update, context):
    logger.info("get_ps started")
    try:
        stdin, stdout, stderr = client.exec_command('ps -a')
        text = "*Запущенные процессы:*\n```\n" + (stdout.read() + stderr.read()).decode() + "\n```"

        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info("get_ps OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_ss(update: Update, context):
    logger.info("get_ss started")
    try:
        stdin, stdout, stderr = client.exec_command('ss -tlpn')
        text = "*Используемые порты:*\n```\n" + (stdout.read() + stderr.read()).decode() + "\n```"

        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info("get_ss OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_apt_list(update: Update, context):
    logger.info("get_apt_list started")
    try:
        if len(context.args) == 0:
            stdin, stdout, stderr = client.exec_command("dpkg-query -f '${binary:Package}\n' -W")
            text = (stdout.read() + stderr.read()).decode().split("\n")[:-1]

            packets = text[0]

            for i in text[1:]:
                if len(packets + ", " + i) <= 4096:
                    packets += ", " + i
                else:
                    update.message.reply_text(packets)
                    packets = ""
                    sleep(1)
            if packets != "":
                update.message.reply_text(packets)
        elif len(context.args) == 1:
            stdin, stdout, stderr = client.exec_command(f'apt show {context.args[0]}')
            text = (stdout.read() + stderr.read()).decode()

            update.message.reply_text(text)
        logger.info("get_apt_list OK")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error: {e}")


def get_services(update: Update, context):
    logger.info("get_services started")
    try:
        stdin, stdout, stderr = client.exec_command(f'systemctl list-units --type=service')
        services = (stdout.read() + stderr.read()).decode().split("\n")[:-6]
        text = "*Список сервисов:*\n```\n"
        for i in services:
            if len(text + i + "\n") <= 4096:
                text += i + "\n"
            else:
                text += "```"
                update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
                text = "```\n"
                sleep(1)
        if text != "```\n":
            text += "```"
            update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info("get_services OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_repl_logs(update: Update, context):
    logger.info("get_repl_logs started")
    try:
        stdin, stdout, stderr = client.exec_command(f'cat /var/log/postgresql/postgresql-15-main.log')
        text = (stdout.read() + stderr.read()).decode()
        result = "```\n"
        for line in text.split("\n"):
            logger.info(line)
            if "db-repl-user" in line:
                result += line + "\n"
        result += "```"

        update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info("get_repl_logs OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_emails(update: Update, context):
    logger.info("get_emails started")
    try:
        with DatabaseConnection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM emails;")
            result = "\n".join([f"{i[0]}. {i[1]}" for i in cur.fetchall()])
            cur.close()
            update.message.reply_text(result)

        logger.info("get_emails OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def get_phone_numbers(update: Update, context):
    logger.info("get_phone_numbers started")
    try:
        with DatabaseConnection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM phones;")
            result = "\n".join([f"{i[0]}. {i[1]}" for i in cur.fetchall()])
            cur.close()
            update.message.reply_text(result)

        logger.info("get_phone_numbers OK")
    except Exception as e:
        logger.error(f"Error: {e}")


def main() -> None:
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    conv_handler_find_phone_number = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', find_phone_number_command)],
        states={
            'find_phone_number': [MessageHandler(Filters.text & ~Filters.command, find_phone_number)],
            'save_phones': [MessageHandler(Filters.text & ~Filters.command, save_phone_numbers)],
        },
        fallbacks=[]
    )

    conv_handler_find_email = ConversationHandler(
        entry_points=[CommandHandler("find_email", find_email_command)],
        states={
            'find_email': [MessageHandler(Filters.text & ~Filters.command, find_email)],
            'save_email': [MessageHandler(Filters.text & ~Filters.command, save_email)],
        },
        fallbacks=[]
    )

    conv_handler_verify_password = ConversationHandler(
        entry_points=[CommandHandler("verify_password", verify_password_command)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verify_password)],
        },
        fallbacks=[]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler_find_phone_number)
    dp.add_handler(conv_handler_find_email)
    dp.add_handler(conv_handler_verify_password)
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))

    updater.start_polling()

    updater.idle()
    client.close()


if __name__ == "__main__":
    main()
