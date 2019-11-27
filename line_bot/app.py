#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, render_template, redirect, session, abort
from flask_heroku import Heroku
import re
import os
import random
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

from db import db, User, init_app, add_user, edit_user, get_step

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
    if step == 5:
        if event.message.content_provider.type == 'line':
            message_content = line_bot_api.get_message_content(event.message.id)
            tmp = io.BytesIO()
            for chunk in message_content.iter_content():
                tmp.write(chunk)
            res = decode(Image.open(tmp))
            print(res)
            if len(res) > 0:
                edit_user(line_id, {"add_friend_url": res[0].data.decode()}, increment_step=True)


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
        text = "你是否願意參加公視的紀錄行動？\n我們與公視合作，正在策劃一個節目內容，記錄對談過程。如果你有意願參加，請選「是」。留意後續的 Line 加好友通知，會有「公視P#新聞實驗室」的夥伴跟你聯繫。"
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
        messages.append(TextSendMessage(text="台灣需要你！快來加入「多粉對談」(點選 https://line.me/R/ti/p/%40843xetsu )，與不同政治陣營的人對談，傾聽並了解彼此的想法。突破同溫層從自己開始。活動網址：taiwan2020.org"))
        reply(event, messages)
    elif step > 5:
        reply(event, TextSendMessage(text="若有任何問題，請上活動網站taiwan2020.org，或寄信到wenhshaw@gmail.com，聯絡我們。"))

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
    respond_by_step(step, event, line_id)

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


def send_pairing_message(to_id, contact, line_or_phone='line'):
    if line_or_phone == 'line':
        message = TextSendMessage(text="""恭喜你配對成功🎉！ 感謝你願意來進行「多粉對談」。

請你點選連結 (%s )，將你配對的人加入好友，然後與他約一個適合的時間，進行對話。建議可以從30-60分鐘開始，透過語音交談。
以下的談話原則可以幫助對話：

1. 傾聽：積極聆聽並發問，表現你對他講話的有興趣。
2. 使用「我」開頭：不要講「你們都」怎樣，使用「我」開頭的句子，從自己的經驗出發。
3. 轉換批評成期望：轉換批評「某某某就完全忽略城鄉差距啊！」，成為期望「我希望某某某更關心城鄉差距」
4. 等他講完：等對方完成他的句子再回話。
5. 接受不自在：有差異和歧見是完全正常的，我們可以從差異和歧見學到很多

我們想了些破冰問題，給你參考：
1. 你在哪裡長大的？家庭是怎麼樣子？長大的過程如何？
2. 你怎麼會想來參加「多粉對談」？
3. 你對於現在生活最滿意的事是什麼？最想改變的是什麼？
4. 你對現在的台灣最滿意的是什麼？最想改變的是什麼？

兩到三題破冰之後，我們建議一些討論話題：
1. 你支持哪一位2020總統候選人？為什麼？
2. 你喜歡我支持的候選人任何地方嗎？
3. 你對於目前選舉有什麼感覺？
4. 如果你想要我這邊的候選人改變一件事情，那會是什麼？為什麼？
5. 分享一則新聞：分享一則想要對方知道的新聞，說明原因並討論。

最後，我們建議以下步驟做收尾：
1. 詢問對方：你覺得在今天對話後有什麼感覺不同嗎？
2. 感謝對方，謝謝他願意花時間鼓起勇氣與你對談。
3. 分享你的回饋和談話後感受到 wenhshaw@gmail.com，我們很期待聽到你的感受與想法！
4. 也歡迎分享你的回饋在臉書上，使用 #多粉對談 標籤。

記得，我們的目標是了解在同個土地生活的彼此。我會晚一點跟你們追蹤一下狀況的。祝談話愉快！
    """ % contact)
    elif line_or_phone == 'phone':
        message = TextSendMessage(text="""恭喜你配對成功🎉！ 感謝你願意來進行「多粉對談」。

請你打電話或傳訊息給你配對的人 (%s )，與他約一個適合的時間對話。他也收到了這份訊息，所以已有準備與你聯絡。建議可以從30-60分鐘開始，透過電話交談。
以下的談話原則可以幫助對話：

1. 傾聽：積極聆聽並發問，表現你對他講話的有興趣。
2. 使用「我」開頭：不要講「你們都」怎樣，使用「我」開頭的句子，從自己的經驗出發。
3. 轉換批評成期望：轉換批評「某某某就完全忽略城鄉差距啊！」，成為期望「我希望某某某更關心城鄉差距」
4. 等他講完：等對方完成他的句子再回話。
5. 接受不自在：有差異和歧見是完全正常的，我們可以從差異和歧見學到很多

我們想了些破冰問題，給你參考：
1. 你在哪裡長大的？家庭是怎麼樣子？長大的過程如何？
2. 你怎麼會想來參加「多粉對談」？
3. 你對於現在生活最滿意的事是什麼？最想改變的是什麼？
4. 你對現在的台灣最滿意的是什麼？最想改變的是什麼？

兩到三題破冰之後，我們建議一些討論話題：
1. 你支持哪一位2020總統候選人？為什麼？
2. 你喜歡我支持的候選人任何地方嗎？
3. 你對於目前選舉有什麼感覺？
4. 如果你想要我這邊的候選人改變一件事情，那會是什麼？為什麼？
5. 分享一則新聞：分享一則想要對方知道的新聞，說明原因並討論。

最後，我們建議以下步驟做收尾：
1. 詢問對方：你覺得在今天對話後有什麼感覺不同嗎？
2. 感謝對方，謝謝他願意花時間鼓起勇氣與你對談。
3. 分享你的回饋和談話後感受到 wenhshaw@gmail.com，我們很期待聽到你的感受與想法！
4. 也歡迎分享你的回饋在臉書上，使用 #多粉對談 標籤。

記得，我們的目標是了解在同個土地生活的彼此。我會晚一點跟你們追蹤一下狀況的。祝談話愉快！
    """ % contact)
    push(to_id, message)

def pair_users():
    # do the ones with add_friend_url first
    non_tsai_users = User.query.filter(User.candidate!= "蔡英文").all()
    non_tsai_users = [u for u in non_tsai_users
        if u.paired_user_id is None
        and None not in [u.line_id, u.candidate, u.add_friend_url]
    ]
    tsai_users = User.query.filter(User.candidate== "蔡英文").all()
    tsai_users = [u for u in tsai_users
        if u.paired_user_id is None
        and None not in [u.line_id, u.candidate, u.add_friend_url]
        and u.pts_show == '是'
    ]
    targeted_tsai_users = User.query.filter(User.id = 89).all()
    targeted_tsai_users = [u for u in targeted_tsai_users
        if u.paired_user_id is None
        and None not in [u.line_id, u.candidate, u.add_friend_url]
        and u.pts_show == '是'
    ]

    print("num of non-tsai users: %s" % len(non_tsai_users))
    print("num of tsai users: %s" % len(tsai_users))
    print("num of targeted tsai users: %s" % len(targeted_tsai_users))
    for non_tsai in non_tsai_users:
        if len(targeted_tsai_users) > 0:
            tsai = random.choice(targeted_tsai_users)
        else:
            tsai = random.choice(tsai_users)
        print("Non Tsai: candidate: %s. phone: %s. url: %s. " % (non_tsai.candidate, non_tsai.phone_number, non_tsai.add_friend_url))
        print("Tsai: candidate: %s. phone: %s. url: %s. " % (tsai.candidate, tsai.phone_number, tsai.add_friend_url))
        v = input("continue (y/n)?")
        if v == 'n':
            continue
        send_pairing_message(tsai.line_id, non_tsai.add_friend_url, 'line')
        send_pairing_message(non_tsai.line_id, tsai.add_friend_url, 'line')
        tsai.paired_user_id = non_tsai.id
        non_tsai.paired_user_id = tsai.id
        db.session.add(tsai)
        db.session.add(non_tsai)
        db.session.commit()
        if tsai in tsai_users:
            tsai_users.remove(tsai)
        else:
            targeted_tsai_users.remove(tsai)
    print("AFTER: num of tsai users: %s" % len(tsai_users))
    print("AFTER: num of targeted tsai users: %s" % len(targeted_tsai_users))
    print("AFTER: ids of paired non tsai users: %s" % [u.id for u in non_tsai_users])
    print("Now processing ones with only phone numbers")
    non_tsai_users = User.query.filter(User.candidate!= "蔡英文").all()
    non_tsai_users = [u for u in non_tsai_users
        if u.paired_user_id is None
        and None not in [u.line_id, u.candidate, u.phone_number]
    ]
    tsai_users = User.query.filter(User.candidate== "蔡英文").all()
    tsai_users = [u for u in tsai_users
        if u.paired_user_id is None
        and None not in [u.line_id, u.candidate, u.phone_number]
        and u.pts_show == '是'
    ]
    print("num of non-tsai users: %s" % len(non_tsai_users))
    print("num of tsai users: %s" % len(tsai_users))
    for non_tsai in non_tsai_users:
        tsai = random.choice(tsai_users)
        print("Non Tsai: id: %s. candidate: %s. phone: %s. url: %s. " % (non_tsai.id, non_tsai.candidate, non_tsai.phone_number, non_tsai.add_friend_url))
        print("Tsai: id: %s. candidate: %s. phone: %s. url: %s. " % (tsai.id, tsai.candidate, tsai.phone_number, tsai.add_friend_url))
        v = input("continue (y/n)?")
        if v == 'n':
            continue
        send_pairing_message(tsai.line_id, non_tsai.phone_number, 'phone')
        send_pairing_message(non_tsai.line_id, tsai.phone_number, 'phone')
        tsai.paired_user_id = non_tsai.id
        non_tsai.paired_user_id = tsai.id
        db.session.add(tsai)
        db.session.add(non_tsai)
        db.session.commit()
        tsai_users.remove(tsai)
    print("AFTER: num of tsai users: %s" % len(tsai_users))
    print("ids of paired non tsai users: %s" % [u.id for u in non_tsai_users])

if __name__ == "__main__":
    app.run(debug=True)
