#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import requests
import datetime
import hashlib
import base64
import hmac
import json

class get_result(object):
    def __init__(self, host):
        self.APPID = os.environ.get("XFYUN_APP_ID", "")
        self.Secret = os.environ.get("XFYUN_API_SECRET", "")
        self.APIKey = os.environ.get("XFYUN_API_KEY", "")

        self.Host = host
        self.RequestUri = "/v2/ocr"
        self.url = "https://" + host + self.RequestUri
        self.HttpMethod = "POST"
        self.Algorithm = "hmac-sha256"
        self.HttpProto = "HTTP/1.1"

        curTime_utc = datetime.datetime.utcnow()
        self.Date = self.httpdate(curTime_utc)

        self.AudioPath = "fingerocr/1.jpg"
        self.BusinessArgs = {
            "ent": "fingerocr",
            "mode": "finger+ocr",
            "method": "dynamic",
            "resize_w": 1088,
            "resize_h": 1632,
        }

    def imgRead(self, path):
        with open(path, 'rb') as fo:
            return fo.read()

    def hashlib_256(self, res):
        m = hashlib.sha256(bytes(res.encode(encoding='utf-8'))).digest()
        result = "SHA-256=" + base64.b64encode(m).decode(encoding='utf-8')
        return result

    def httpdate(self, dt):
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                 "Oct", "Nov", "Dec"][dt.month - 1]
        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
                                                        dt.year, dt.hour, dt.minute, dt.second)

    def generateSignature(self, digest):
        signatureStr = "host: " + self.Host + "\n"
        signatureStr += "date: " + self.Date + "\n"
        signatureStr += self.HttpMethod + " " + self.RequestUri + " " + self.HttpProto + "\n"
        signatureStr += "digest: " + digest
        signature = hmac.new(bytes(self.Secret.encode(encoding='utf-8')),
                             bytes(signatureStr.encode(encoding='utf-8')),
                             digestmod=hashlib.sha256).digest()
        result = base64.b64encode(signature)
        return result.decode(encoding='utf-8')

    def init_header(self, data):
        digest = self.hashlib_256(data)
        sign = self.generateSignature(digest)
        authHeader = 'api_key="%s", algorithm="%s", headers="host date request-line digest", signature="%s"' \
                     % (self.APIKey, self.Algorithm, sign)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Method": "POST",
            "Host": self.Host,
            "Date": self.Date,
            "Digest": digest,
            "Authorization": authHeader
        }
        return headers

    def get_body(self):
        audioData = self.imgRead(self.AudioPath)
        content = base64.b64encode(audioData).decode(encoding='utf-8')
        postdata = {
            "common": {"app_id": self.APPID},
            "business": self.BusinessArgs,
            "data": {
                "image": content,
            }
        }
        body = json.dumps(postdata)
        return body

    def call_url(self):
        def find_nearest_word(respData):
            try:
                finger_x = respData["data"]["finger_pos"]["pos_x"]
                finger_y = respData["data"]["finger_pos"]["pos_y"]
                words = respData["data"]["finger_ocr"]["word"]["list"]
                min_dist = float('inf')
                closest_word = None
                for word in words:
                    coords = word.get("coord", [])
                    if len(coords) != 4:
                        continue
                    center_x = sum(p["x"] for p in coords) / 4
                    center_y = sum(p["y"] for p in coords) / 4
                    dist = ((center_x - finger_x) ** 2 + (center_y - finger_y) ** 2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        closest_word = word.get("content", "")
                return closest_word
            except Exception as e:
                print(f"❌ 查找最近单词失败: {e}")
                return None

        if self.APPID == '' or self.APIKey == '' or self.Secret == '':
            print('Appid 或APIKey 或APISecret 为空！请填写信息。')
        else:
            body = self.get_body()
            headers = self.init_header(body)
            response = requests.post(self.url, data=body, headers=headers, timeout=8)
            if response.status_code != 200:
                print("Http请求失败，状态码：" + str(response.status_code) + "，错误信息：" + response.text)
            else:
                respData = json.loads(response.text)

                # ✅ 获取 word.list[0]
                try:
                    word_list = respData["data"]["finger_ocr"]["word"]["list"]
                    if word_list:
                        first_word = word_list[0].get("content", "")
                        print("📌 第一个识别单词是:", first_word)
                    else:
                        print("⚠️ 未识别出任何单词")
                except Exception as e:
                    print(f"❌ 提取第一个单词失败: {e}")

                # ✅ 错误码提示
                code = str(respData.get("code", "0"))
                if code != '0':
                    print("请前往 https://www.xfyun.cn/document/error-code?code=" + code + " 查询解决办法")



if __name__ == '__main__':
    host = "tyocr.xfyun.cn"
    gClass = get_result(host)
    gClass.call_url()
