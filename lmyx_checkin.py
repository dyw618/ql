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

import json
import os
import sys
import time

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
        "Accept-Encoding": "gzip, deflate",  # 移除 br 和 zstd
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

        if resp.status_code != 200:
            return False, f"HTTP 状态码 {resp.status_code}", ""

        content_type = resp.headers.get('content-type', '')
        if 'application/json' not in content_type:
            return False, f"响应非 JSON (Content-Type: {content_type})", ""

        try:
            resp_json = resp.json()
        except json.JSONDecodeError as e:
            return False, f"JSON 解析失败: {e}\n响应内容前200字符: {resp.text[:200]}", ""

        if not isinstance(resp_json, dict):
            return False, f"响应类型错误: {type(resp_json)}，内容片段: {resp.text[:200]}", ""

        # 业务判断
        if resp_json.get("error") is False:
            msg = resp_json.get("msg", "")
            points = resp_json.get("data", {}).get("points", 0)
            integral = resp_json.get("data", {}).get("integral", 0)
            continuous = resp_json.get("continuous_day", 0)
            detail = f"连续签到 {continuous} 天，获得积分 {points}，经验 {integral}"
            return True, msg, detail
        else:
            err = resp_json.get("msg", "未知错误")
            return False, f"签到失败: {err}", ""

    except requests.exceptions.RequestException as e:
        # 网络异常（包括超时、连接错误等）
        return False, f"网络异常: {str(e)}", ""
    except Exception as e:
        return False, f"请求异常: {str(e)}", ""


# ---------- 主函数（含重试） ----------
def main():
    cookie = os.getenv("lmyx_CK")
    if not cookie:
        print("❌ 未设置环境变量 lmyx_CK")
        send_notify("老木社区签到失败", "未设置环境变量 lmyx_CK")
        sys.exit(1)

    max_retries = 3
    retry_interval = 600  # 10分钟（秒）

    for attempt in range(1, max_retries + 1):
        print(f"\n========== 老木社区签到 (尝试 {attempt}/{max_retries}) ==========")
        success, msg, detail = sign_in(cookie.strip())

        if success:
            print(f"✅ {msg}")
            print(f"📊 {detail}")
            send_notify("老木社区签到结果", f"{msg}\n{detail}")
            return

        # 签到失败
        print(f"❌ {msg}")

        # 判断是否因超时或网络问题导致
        error_lower = msg.lower()
        is_timeout = any(keyword in error_lower for keyword in ["timeout", "timed out", "connection"])

        if is_timeout and attempt < max_retries:
            print(f"⏰ 网络超时，等待 {retry_interval // 60} 分钟后重试...")
            time.sleep(retry_interval)
            continue
        else:
            # 非超时错误 或 已达最大重试次数
            if is_timeout and attempt == max_retries:
                print("❌ 多次重试后仍然超时，退出")
            else:
                # 其他业务错误（如 Cookie 失效），不重试
                print("❌ 非网络错误，直接退出")
            send_notify("老木社区签到失败", msg)
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"脚本异常: {e}")
        send_notify("老木社区签到异常", str(e))
