# -*- coding: utf-8 -*-
"""
cron: 30 11 * * *
new Env('得物0元抽')
网址：app.dewu.com/api
环境变量：dwck = x-auth-token（去掉Bearer）
多账号用 & 或 换行 分隔
"""

import hashlib
import json
import os

import requests

# ================= 配置 =================
ENV_NAME = "dwck"
SPLIT_CHAR = "&"
VERSION = "5.89.0"
SECRET_KEY = "048a9c4943398714b356a696503d2d36"
# ========================================

msg_all = ""


# 读取环境变量
def load_env():
    ck = os.getenv(ENV_NAME)
    if not ck:
        print("未配置环境变量 dwck")
        return []
    accounts = ck.replace("\n", SPLIT_CHAR).split(SPLIT_CHAR)
    accounts = [a.strip() for a in accounts if a.strip()]
    return accounts


# 签名算法
def calculate_sign(body):
    try:
        sorted_keys = sorted(body.keys())
        sign_str = ""
        for key in sorted_keys:
            val = body[key]
            if val is None:
                continue
            if isinstance(val, dict):
                sign_str += key + json.dumps(val, ensure_ascii=False, separators=(',', ':'))
            elif isinstance(val, list):
                sign_str += key + "".join(str(i) for i in val)
            else:
                sign_str += key + str(val)
        md5 = hashlib.md5()
        md5.update((sign_str + SECRET_KEY).encode("utf-8"))
        return md5.hexdigest().lower()
    except:
        return ""


# 请求工具
def req(token, url, data=None):
    data = data or {}
    sign = calculate_sign(data)
    url = f"{url}{'&' if '?' in url else '?'}sign={sign}"

    headers = {
        "Host": "app.dewu.com",
        "User-Agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_15 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148/duapp/{VERSION}",
        "x-auth-token": f"Bearer {token}",
        "Content-Type": "application/json",
        "platform": "h5",
        "appVersion": VERSION,
        "v": VERSION,
        "channel": "App Store",
        "networktype": "WIFI",
        "deviceTrait": "iPhone",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        return resp.json()
    except Exception as e:
        return {"code": -1, "msg": str(e)}


# 执行单个账号
def run_user(token, idx):
    global msg_all
    log = f"【账号{idx}】"
    print(log + "开始执行")

    url1 = "https://app.dewu.com/api/v1/h5/oss-platform/hacking-zero-lottery/v1/activity/query-today"
    res = req(token, url1, {"source": "wotab"})

    if res.get("code") != 200 or not res.get("data", {}).get("activityList"):
        err = log + "获取活动失败：" + res.get("msg", "接口异常")
        print(err)
        msg_all += err + "\n"
        return

    success = 0
    fail = 0
    for item in res["data"]["activityList"]:
        if item.get("status") != 0:
            continue

        url2 = "https://app.dewu.com/hacking-zero-lottery/v1/activity/engage-in"
        data2 = {"id": item["id"], "source": "wotab", "inner": True}
        join = req(token, url2, data2)

        if join.get("code") == 200:
            success += 1
            print(log + f"参与【{item.get('title', '未知活动')}】成功")
        else:
            fail += 1

    result = log + f"执行完成：成功 {success} 次 | 失败 {fail} 次"
    print(result)
    msg_all += result + "\n"


# 主函数
if __name__ == "__main__":
    print("===== 得物0元抽 Python 纯净版 =====")
    accounts = load_env()
    if not accounts:
        exit()

    print(f"共加载 {len(accounts)} 个账号")
    for i, token in enumerate(accounts, 1):
        run_user(token, i)

    print("\n===== 执行结果汇总 =====")
    print(msg_all)
