#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一步两步游戏 每日签到（单账户，仅需 Token）
cron: 8 20 * * *
const $ = new Env("一步两步签到");

环境变量：
    FY_TOKEN  - 必填，Authorization 头中的 Bearer Token（不含 "Bearer " 前缀）
"""

import base64
import json
import os
import sys

import requests

# ---------- 通知模块加载 ----------
has_notify = False
try:
    from notify import send

    has_notify = True
except ImportError:
    pass


def send_notify(title, content):
    if has_notify:
        try:
            send(title, content)
            print("✅ 通知已发送")
        except Exception as e:
            print(f"❌ 通知发送失败: {e}")
    else:
        print(f"📢 {title}\n{content}")


# ---------- 配置 ----------
TOKEN = os.getenv("FY_TOKEN")
if not TOKEN:
    print("❌ 未设置 FY_TOKEN")
    send_notify("签到失败", "请设置 FY_TOKEN")
    sys.exit(1)


# 从 JWT 中解析 user_id（payload 部分）
def decode_jwt_payload(token):
    try:
        # JWT 格式: header.payload.signature，取第二部分
        payload_part = token.split('.')[1]
        # Base64URL 解码，需要补足 '=' 填充
        payload_part += '=' * (4 - len(payload_part) % 4)
        payload_json = base64.urlsafe_b64decode(payload_part).decode('utf-8')
        payload = json.loads(payload_json)
        return payload.get('user_id')
    except Exception as e:
        print(f"解析 Token 失败: {e}")
        return None


USER_ID = decode_jwt_payload(TOKEN)
if not USER_ID:
    print("❌ 无法从 Token 中解析 user_id，请检查 Token 是否有效")
    send_notify("一步两步签到失败", "Token 无效，无法解析 user_id")
    sys.exit(1)

# 固定请求头（抓包值）
BASE_URL = "https://api-yblbsns.feiyu.com"
HEADERS = {
    "Host": "api-yblbsns.feiyu.com",
    "content-type": "application/json",
    "x-user-id": USER_ID,
    "Authorization": f"Bearer {TOKEN}",
    "x-device-id": "b988777d89144d9961193672c5a145a4",
    "x-user-uuid": "oPIgF7nvA90378gxem0Nfhgexq1g",
    "x-game-id": "1",
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.75(0x18004b66) NetType/WIFI Language/zh_CN",
    "Referer": "https://servicewechat.com/wxc58548c15bde03ab/13/page-frame.html"
}


def query_sign_status():
    """查询签到列表和今日签到状态"""
    url = f"{BASE_URL}/v1/sign/daily/list"
    try:
        resp = requests.post(url, headers=HEADERS, json={}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == 0:
            return data.get("data", {})
        else:
            print(f"查询签到状态失败: {data.get('message')}")
            return None
    except Exception as e:
        print(f"查询签到状态异常: {e}")
        return None


def do_sign():
    """执行签到"""
    url = f"{BASE_URL}/v1/user/checkIn"
    try:
        resp = requests.post(url, headers=HEADERS, json={}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == 0:
            return True, data.get("message", "签到成功")
        else:
            return False, data.get("message", "未知错误")
    except Exception as e:
        return False, f"请求异常: {e}"


def get_gift_name(gifts, cum_days):
    """从奖励列表中查找对应天数的奖励名称"""
    for gift in gifts:
        if gift.get("cum_days") == cum_days:
            return gift.get("gift_name", "")
    return ""


# ---------- 主函数 ----------
def main():
    print("========== 一步两步游戏签到 ==========")
    print(f"用户ID: {USER_ID}")

    # 1. 查询今日签到状态
    sign_data = query_sign_status()
    if sign_data is None:
        print("❌ 获取签到状态失败，退出")
        send_notify("一步两步签到失败", "获取签到状态失败")
        return

    has_signed = sign_data.get("has_signed_today", False)
    cum_days = sign_data.get("cum_days", 0)
    gifts = sign_data.get("gifts", [])  # 获取奖励列表
    print(f"累计签到天数: {cum_days}")
    print(f"今日已签到: {has_signed}")

    if has_signed:
        reward = get_gift_name(gifts, cum_days)
        reward_text = f"，第{cum_days}天奖励：{reward}" if reward else ""
        msg = f"今日已签到，累计 {cum_days} 天{reward_text}"
        print(f"✅ {msg}")
        send_notify("签到结果", msg)
        return

    # 2. 执行签到
    print("执行签到...")
    success, result = do_sign()
    if success:
        # 签到成功后重新查询最新数据
        new_data = query_sign_status()
        if new_data:
            new_days = new_data.get("cum_days", cum_days)
            new_gifts = new_data.get("gifts", [])
            reward = get_gift_name(new_gifts, new_days)
            reward_text = f"，第{new_days}天奖励：{reward}" if reward else ""
            final_msg = f"{result}，累计签到 {new_days} 天{reward_text}"
        else:
            final_msg = f"{result}，累计签到 {cum_days} 天"
        print(f"✅ {final_msg}")
        send_notify("一步两步签到成功", final_msg)
    else:
        print(f"❌ 签到失败: {result}")
        send_notify("一步两步签到失败", result)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"脚本异常: {e}"
        print(error_msg)
        send_notify("一步两步签到异常", error_msg)
