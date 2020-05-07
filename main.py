#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is a simple echo bot using decorators and webhook with aiohttp
# It echoes any incoming text messages and does not use the polling method.

import logging
import ssl
from datetime import datetime, timedelta
import time
from aiohttp import web

import telebot

API_TOKEN = 'TOKEN'

WEBHOOK_HOST = 'DOMAIN'
WEBHOOK_PORT = 8443  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

WEBHOOK_SSL_CERT = 'CERT.PEM'  # Path to the ssl certificate
WEBHOOK_SSL_PRIV = 'PRIVKEY.PEM'  # Path to the ssl private key

# Quick'n'dirty SSL certificate generation:
#
# openssl genrsa -out webhook_pkey.pem 2048
# openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem
#
# When asked for "Common Name (e.g. server FQDN or YOUR name)" you should reply
# with the same value in you put in WEBHOOK_HOST

WEBHOOK_URL_BASE = "https://{}:{}".format(WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/{}/".format(API_TOKEN)

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(API_TOKEN)

app = web.Application()

text_messages = {
    'welcome':
        u'歚迎 {name} 來到此Group\n'
        u'由於安全及私穩問題,你需按下按鈕進行問題回答\n'
        u'回答正確後,你的發言權限將會回復正常\n'
}

question = {}

# Process webhook calls


async def handle(request):
    if request.match_info.get('token') == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return web.Response()
    else:
        return web.Response(status=403)


app.router.add_post('/{token}/', handle)


def countdown(t):
    while t:
        mins, secs = divmod(t, 60)
        timer = '{:02d}:{:02d}'.format(mins, secs)
        print(timer, end="\r")
        time.sleep(1)
        t -= 1
    return 0


def gen_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(telebot.types.InlineKeyboardButton("{ans_1}".format(), callback_data="ans_1"), telebot.types.InlineKeyboardButton(
        "{ans_2}".format(), callback_data="ans_2"), telebot.types.InlineKeyboardButton("{ans_3}".format(), callback_data="ans_3"))
    return markup


def demsg(id, message):
    time.sleep(5)
    bot.delete_message(message.chat_id, id)


def verify(message):
    msg_1_id = bot.send_message(message.chat_id, "請在60秒內回答以下問題")
    timer = datetime.now().strftime("%M:%S")
    msg_rand_id = bot.send_message(message.chat_id, "請輸入 : 中國武漢肺炎")
    while countdown(int(60)) != 0:
        while message.text == "中國武漢肺炎":
            bot.restrict_chat_member(
                message.chat_id, message.user_id, None, True, True, True, True, True)
            bot.send_message(message.chat_id, "用戶"+message+"已通過")
            return
        bot.delete_message(message.chat_id, bot.message_id)
        msg_id_1 = bot.send_message(message.chat_id, "驗証錯誤,請重新輸入 \n本信息5秒後自動刪除")
        demsg(msg_id_1, message)
    bot.send_message(message.chat_id, "驗証已超時,請向管理員手動調解")


# Handle new member
@bot.message_handler(func=lambda m: True, content_types=['new_chat_participant'])
def on_user_joins(message):
    if bot.get_chat_administrators is not []:
        bot.reply_to(message, "本 bot 需要 刪除信息,封鎖用戶 權限才能正常運作")
        return

    name = message.new_chat_participant.first_name
    bot.restrict_chat_member(
        message.chat_id, message.user_id, None, False, False, False, False, False)
    if hasattr(message.new_chat_participant, 'last_name') and message.new_chat_participant.last_name is not None:
        name += u" {}".format(message.new_chat_participant.last_name)

    if hasattr(message.new_chat_participant, 'username') and message.new_chat_participant.username is not None:
        name += u" (@{})".format(message.new_chat_participant.username)

    msg = bot.send_message(message, text_messages['welcome'].format(name=name))
    bot.register_next_step_handler(msg, verify)

# Handle all other messages
# @bot.message_handler(func=lambda message: True, content_types=['text'])
# def echo_message(message):
#     bot.reply_to(message, message.text)


# Remove webhook, it fails sometimes the set if there is a previous webhook
bot.remove_webhook()

# Set webhook
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))

# Build ssl context
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)

# Start aiohttp server
web.run_app(
    app,
    host=WEBHOOK_LISTEN,
    port=WEBHOOK_PORT,
    ssl_context=context,
)
