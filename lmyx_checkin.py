#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
老木社区 每日签到
cron: 13 13 * * *
const $ = new Env("老木社区签到");

环境变量：
    lmyx_CK  - 必填，从抓包中获取的 Cookie 字符串（完整复制）
                      多账号用换行分隔，每行一个 Cookie
"""

import os
import sys

import requests
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


# ---------- 签到函数 ----------
def sign_in(cookie):
    url = "https://laomuxs.cn/wp-admin/admin-ajax.php"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie,
        "Host": "laomuxs.cn",
        "Origin": "https://laomuxs.cn",
        "Referer": "https://laomuxs.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }
    data = {"action": "user_checkin"}

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=30, verify=False)
        resp_json = resp.json()
        if resp.status_code == 200 and resp_json.get("error") is False:
            msg = resp_json.get("msg", "")
            # msg = msg.encode('utf-8').decode('unicode_escape')
            points = resp_json.get("data", {}).get("points", 0)
            integral = resp_json.get("data", {}).get("integral", 0)
            continuous = resp_json.get("continuous_day", 0)
            detail = f"连续签到 {continuous} 天，获得积分 {points}，经验 {integral}"
            return True, msg, detail
        else:
            err = resp_json.get("msg", "未知错误")
            # err = err.encode('utf-8').decode('unicode_escape')
            return False, f"签到失败: {err}", ""
    except Exception as e:
        return False, f"请求异常: {str(e)}", ""


# ---------- 主函数 ----------
def main():
    cookie = os.getenv("lmyx_CK")
    if not cookie:
        print("❌ 未设置环境变量 lmyx_CK")
        send_notify("老木社区签到失败", "未设置环境变量 lmyx_CK")
        sys.exit(1)

    print("========== 老木社区签到 ==========")

    success, msg, detail = sign_in(cookie.strip())
    if success:
        print(f"✅ {msg}")
        print(f"📊 {detail}")
    else:
        print(f"❌ {msg}")

    # 发送通知（包含完整信息）
    content = f"{msg}\n{detail}" if success else msg
    send_notify("老木社区签到结果", content)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"脚本异常: {e}")
        send_notify("老木社区签到异常", str(e))
