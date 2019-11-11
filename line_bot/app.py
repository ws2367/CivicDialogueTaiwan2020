#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, render_template, redirect, session, abort
from flask_heroku import Heroku
import re
import os
from pyzbar.pyzbar import decode
from PIL import Image
import io
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    FollowEvent, UnfollowEvent, MessageEvent, JoinEvent, TextMessage, TextSendMessage, ImageMessage,
    QuickReply, QuickReplyButton, MessageAction, URIAction, ImageSendMessage,
    TemplateSendMessage, ImageCarouselColumn, ImageCarouselTemplate, PostbackAction
)

from db import db, init_app, add_user, edit_user, get_step

app = Flask(__name__)
heroku = Heroku(app)
init_app(app)

CHANNEL_ACCESS_TOKEN = "HJ56LZmSCt9Xiv+xaZvzi37fGODgJxWADtS3sp2jOS8MNsDQUjbPUyPR6fG8mSddy2G2XMXAQtekabEwZ69Spjtq/WOyjR1DV3dYKHUIztXFYV2aOxSufCQk7PwjSS4tMoK8AY3la/qkYX4IHbRVIgdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "249e5e165d90bba4918ed54e4c675a5e"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

CANDIDATES = ["韓國瑜", "蔡英文"]
AGE_GROUPS = ["20歲以下", "20-40歲", "40-60歲", "60歲以上", "不想回答"]
YES_OR_NO = ["是", "否"]


# ========================


def share_friending_url_carousel_message():
    return TemplateSendMessage(
    alt_text='傳送你加好友連結給多粉對談',
    template=ImageCarouselTemplate(
        columns=[
            ImageCarouselColumn(
                image_url='https://taiwan2020.org/img/share_friending_url_1.PNG',
                action=PostbackAction(
                    data='nullrequest'
                )
            ),
            ImageCarouselColumn(
                image_url='https://taiwan2020.org/img/share_friending_url_2.PNG',
                action=PostbackAction(
                    data='nullrequest'
                )
            ),
            ImageCarouselColumn(
                image_url='https://taiwan2020.org/img/share_friending_url_3.PNG',
                action=PostbackAction(
                    data='nullrequest'
                )
            ),
            ImageCarouselColumn(
                image_url='https://taiwan2020.org/img/share_friending_url_4.PNG',
                action=PostbackAction(
                    data='nullrequest'
                )
            )
        ]
    )
)

@handler.add(UnfollowEvent)
def handle_unfollow(event):
    if event.source.type == 'user':
        line_id = event.source.user_id
        edit_user(line_id, {'following': False})

@handler.add(FollowEvent)
def handle_follow(event):
    print(event.type)
    if event.source.type == 'user':
        line_id = event.source.user_id
        user = add_user(line_id)
        edit_user(line_id, {'following': True})
        if user.step == 0: # step 0 is to send welcome msg and candidate question
            messages = [TextSendMessage(text="你好！很高興你願意加入「多粉對談」，這個活動會配對兩位支持不同政治陣營的人，讓他們進行對談，傾聽並了解彼此的想法。更多資訊請看taiwan2020.org")]
            messages.append(create_quick_replies(
                "2020台灣總統大選你支持哪位候選人？",
                [[i,i] for i in CANDIDATES]))
            reply(event, messages)
            edit_user(line_id, {}, increment_step=True)
        else:
            reply(event, TextSendMessage(text="嗨歡迎回來！了解最新動態請到活動網站taiwan2020.org"))

@handler.default()
def default(event):
    print(event)

def save_respones(step, event, line_id):
    if step == 1:
        edit_user(line_id, {"candidate": event.message.text}, increment_step=True)
    elif step == 2:
        edit_user(line_id, {"age_group": event.message.text}, increment_step=True)
    elif step == 3:
        edit_user(line_id, {"phone_number": event.message.text}, increment_step=True)
    elif step == 4:
        edit_user(line_id, {"pts_show": event.message.text}, increment_step=True)
    elif step == 5:
        #extract the URL
        url = extract_url(event.message.text)
        if url is not None:
            edit_user(line_id, {"add_friend_url": url}, increment_step=True)

def save_image_response(step, event, line_id):
    #extract the URL from QR Code
    # if step == 5:
    #     if event.message.content_provider.type == 'line':
     
    message_content = line_bot_api.get_message_content(event.message.id)
    tmp = io.BytesIO()
    for chunk in message_content.iter_content():
        tmp.write(chunk)
    res = decode(Image.open(tmp))
    print(res)
    if len(res) > 0:
        edit_user(line_id, {"add_friend_url": res[0].data}, increment_step=True)


def respond_by_step(step, event, line_id):
    if step == 0:
        reply(event, create_quick_replies(
            "2020台灣總統大選你支持哪位候選人？",
            [[i,i] for i in CANDIDATES]))
        #step 1 is to receive candidate response and send age group qs.
        edit_user(line_id, {}, increment_step=True)
    if step == 1:
        reply(event,
              create_quick_replies("你的年齡範圍？",
              [[i,i] for i in AGE_GROUPS]))
    elif step == 2:
        reply(event, TextSendMessage(text="你的電話號碼是？"))
    elif step == 3:
        text = "你是否願意參加公視的紀錄行動？\n我們與公視合作，正在策劃一個節目內容，記錄對談過程。如果你有意願參加，請選「是」。我們會提供更多細節。"
        reply(event,
              create_quick_replies(text, [[i,i] for i in YES_OR_NO]))
    elif step == 4:
        messages = [TextSendMessage(text="只差最後一步：需要你分享你的QR Code給我們，我們才可以讓你配對的人與你聯繫。下面有圖解，教你如何分享。")]
        messages.append(ImageSendMessage(
            original_content_url='https://taiwan2020.org/img/share_friending_url_1.PNG',
            preview_image_url='https://taiwan2020.org/img/share_friending_url_1.PNG'
        ))
        messages.append(ImageSendMessage(
            original_content_url='https://taiwan2020.org/img/share_friending_url_2.PNG',
            preview_image_url='https://taiwan2020.org/img/share_friending_url_2.PNG'
        ))
        messages.append(ImageSendMessage(
            original_content_url='https://taiwan2020.org/img/share_friending_url_3.PNG',
            preview_image_url='https://taiwan2020.org/img/share_friending_url_3.PNG'
        ))
        messages.append(ImageSendMessage(
            original_content_url='https://taiwan2020.org/img/share_friending_url_4.PNG',
            preview_image_url='https://taiwan2020.org/img/share_friending_url_4.PNG'
        ))
        reply(event, messages)
    elif step == 5:
        messages = [TextSendMessage(text="你已完成報名。一但配對成功，我們就會通知你。\n\n幫我們一起邀請更多朋友來參加「多粉對談」吧。把下面的訊息輕鬆分享出去。")]
        messages.append(TextSendMessage(text="台灣需要你！快來加入「多粉對談」(點選 https://line.me/R/ti/p/%40843xetsu)，與不同政治陣營的人對談，傾聽並了解彼此的想法。突破同溫層從自己開始。活動網址：taiwan2020.org"))
        reply(event, messages)
    elif step > 5:
        reply(event, TextSendMessage(text="若有任何問題，請上活動網站taiwan2020.org，聯絡我們。"))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.source.type != 'user':
        print("ERROR")
        return
    line_id = event.source.user_id
    step = get_step(line_id)
    if step is None:
        user = add_user(line_id)
        step  = user.step
    save_respones(step, event, line_id)
    respond_by_step(step, event, line_id)

@handler.add(MessageEvent, message=ImageMessage)
def handle_message(event):
    line_id = event.source.user_id
    step = get_step(line_id)
    save_image_response(step, event, line_id)


def extract_url(text):
    urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    return urls[0] if len(urls) > 0 else None

def create_quick_replies(reply_text, replies):
    items = []
    for quick_reply in replies:
        quick_label = quick_reply[0]
        quick_text = quick_reply[1]
        button = QuickReplyButton(action=MessageAction(label=quick_label, text=quick_text))
        items.append(button)
    message = TextSendMessage(text=reply_text,
        quick_reply=QuickReply(items=items))
    return message

def push(to_id, message):
    line_bot_api.push_message(
        to_id,
        message)

def reply(event, message):
    line_bot_api.reply_message(
        event.reply_token,
        message)


@app.route('/receive', methods=['GET', 'POST'])
def receive_webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return ('', 204)

if __name__ == "__main__":
    app.run(debug=True)
