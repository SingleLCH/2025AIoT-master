#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import uuid
import json
import base64
import sounddevice as sd
from tencentcloud.common import credential
from tencentcloud.common.exception import TencentCloudSDKException
from tencentcloud.soe.v20180724 import soe_client, models

# 从环境变量获取腾讯云密钥
SECRET_ID  = os.environ.get("TENCENT_SECRET_ID", "")
SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY", "")
REGION     = os.environ.get("TENCENT_REGION", "ap-shanghai")

DURATION = 5
SR       = 16000
REF_TEXT = input("💬 请输入要评测的英文单词（如 apple）: ").strip()

print(f"🎙 录音 {DURATION} 秒，请朗读:  {REF_TEXT}")
audio     = sd.rec(int(DURATION*SR), samplerate=SR, channels=1, dtype='int16')
sd.wait()
pcm_bytes = audio.tobytes()

if not SECRET_ID or not SECRET_KEY:
    print("❌ 错误：请设置环境变量 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY")
    exit(1)
cred   = credential.Credential(SECRET_ID, SECRET_KEY)
client = soe_client.SoeClient(cred, REGION)
req    = models.TransmitOralProcessWithInitRequest()

session_id = str(uuid.uuid4())
params = {
    "SeqId": 1, "IsEnd": 1,
    "VoiceFileType": 1, "VoiceEncodeType": 1,
    "UserVoiceData": base64.b64encode(pcm_bytes).decode(),
    "SessionId": session_id,
    "RefText": REF_TEXT,
    "WorkMode": 1, "EvalMode": 1,
    "ServerType": 0, "ScoreCoeff": 1.0
}
req.from_json_string(json.dumps(params))

try:
    resp   = client.TransmitOralProcessWithInit(req)
    result = json.loads(resp.to_json_string())

    overall_acc  = result.get("PronAccuracy", -1)
    overall_flu  = result.get("PronFluency", -1)
    overall_comp = result.get("PronCompletion", -1)

    print("\n🔎 评测结果（0-100）")
    print(f"  • 准确度  : {overall_acc:.2f}")
    print(f"  • 流利度  : {overall_flu:.2f}")
    print(f"  • 完整度  : {overall_comp:.2f}")

    if result.get("Words"):
        w   = result["Words"][0]
        acc = w.get("PronAccuracy", -1)
        flu = w.get("PronFluency", -1)
        word_text = w.get("Word", REF_TEXT)

        print("\n📌 单词级评分:")
        print(f"  {word_text} -> 准确 {acc:.2f}  流利 {flu:.2f}")

except TencentCloudSDKException as e:
    print("❌ TencentCloudSDKException:", e)
except Exception as e:
    print("❌ 发生未知错误:", e)
