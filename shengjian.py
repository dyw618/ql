#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
声荐小程序签到（每日两次）

打开微信小程序抓取 xcx.myinyun.com:4438 请求中的 authorization 值（Bearer 后的完整Token）
填入环境变量 SJ_SIGN_TOKEN 中即可，支持多用户，每行一个Token。

环境变量：
    SJ_SIGN_TOKEN      - 必填，Bearer Token，多用户用换行分隔
    MAX_RANDOM_DELAY   - 可选，随机延迟最大秒数，默认3600秒（1小时）
    RANDOM_SIGNIN      - 可选，是否启用随机延迟，默认 true

cron: 30 8 * * *
const $ = new Env("声荐签到");
"""

import os
import sys
import time
import random
import requests
from datetime import datetime

# ---------- 统一通知模块加载 ----------
has_notify = False
send_msg = None
try:
    from notify import send
    has_notify = True
    print("✅ 已加载 notify.py 通知模块")
except ImportError:
    print("⚠️ 未找到 notify.py，通知功能将不可用")

# ---------- 随机延迟配置 ----------
MAX_RANDOM_DELAY = int(os.getenv("MAX_RANDOM_DELAY", "3600"))
RANDOM_SIGNIN = os.getenv("RANDOM_SIGNIN", "true").lower() == "true"

def format_time_remaining(seconds):
    """格式化剩余时间"""
    if seconds <= 0:
        return "立即执行"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}小时{minutes}分{secs}秒"
    if minutes > 0:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"

def wait_with_countdown(delay_seconds, task_name):
    """带倒计时的等待"""
    if delay_seconds <= 0:
        return
    print(f"{task_name} 随机延迟 {format_time_remaining(delay_seconds)}")
    remaining = delay_seconds
    while remaining > 0:
        if remaining <= 10 or remaining % 10 == 0:
            print(f"{task_name} 倒计时: {format_time_remaining(remaining)}")
        sleep_sec = 1 if remaining <= 10 else min(10, remaining)
        time.sleep(sleep_sec)
        remaining -= sleep_sec

def notify_user(title, content):
    """统一通知推送"""
    if has_notify:
        try:
            send(title, content)
            print(f"✅ 通知发送完成: {title}")
        except Exception as e:
            print(f"❌ 通知发送失败: {e}")
    else:
        print(f"📢 {title}\n📄 {content}")

# ---------- 日志收集 ----------
all_logs = []

def myprint(msg):
    """收集并打印日志"""
    print(msg)
    all_logs.append(str(msg) + "\n")

# ---------- 签到核心逻辑 ----------
def sign_in(token, sign_no):
    """
    执行签到请求
    :param token: Bearer Token（不含Bearer前缀）
    :param sign_no: 第几次签到（1 或 2）
    :return: (success, message)
    """
    url = "https://xcx.myinyun.com:4438/napi/gift"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Host": "xcx.myinyun.com:4438",
        "Referer": "https://servicewechat.com/wxa25139b08fe6e2b6/23/page-frame.html",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254160e) XWEB/18163",
        "authorization": f"Bearer {token}",
        "xweb_xhr": "1"
    }
    data = {}

    try:
        resp = requests.put(url, headers=headers, json=data, timeout=30)
        resp_json = resp.json()
        myprint(f"第{sign_no}次签到响应状态码: {resp.status_code}")
        myprint(f"第{sign_no}次签到响应内容: {resp_json}")

        # 根据常见签到接口格式判断成功与否
        if resp.status_code == 200:
            code = resp_json.get("code")
            if code == 200 or code == 0 or code is None:
                msg = resp_json.get("msg") or resp_json.get("message") or "签到成功"
                return True, f"第{sign_no}次签到 {msg}"
            else:
                return False, f"第{sign_no}次签到失败 {resp_json.get('msg', f'未知错误 code={code}')}"
        else:
            return False, f"第{sign_no}次签到失败 HTTP {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"第{sign_no}次签到网络异常: {str(e)}"
    except Exception as e:
        return False, f"第{sign_no}次签到解析异常: {str(e)}"

def main():
    """主函数"""
    myprint("========== 声荐每日两次签到开始 ==========")

    # 获取Token列表
    token_env = os.getenv("SJ_SIGN_TOKEN")
    if not token_env:
        myprint("❌ 未找到环境变量 SJ_SIGN_TOKEN，请配置后重试")
        notify_user("声荐签到失败", "未找到环境变量 SJ_SIGN_TOKEN")
        return

    token_list = [t.strip() for t in token_env.replace('\r\n', '\n').split('\n') if t.strip()]
    myprint(f"共获取到 {len(token_list)} 个账号")

    # 随机延迟（整体延迟）
    if RANDOM_SIGNIN:
        delay_sec = random.randint(0, MAX_RANDOM_DELAY)
        if delay_sec > 0:
            wait_with_countdown(delay_sec, "声荐签到")

    total_success = 0
    total_fail = 0

    # 逐个签到
    for idx, token in enumerate(token_list, start=1):
        myprint(f"\n---------- 账号 {idx} ----------")
        # 脱敏显示Token（前4后4）
        token_show = token[:4] + "****" + token[-4:] if len(token) > 8 else "****"
        myprint(f"Token: {token_show}")

        # 每日两次签到
        for i in range(1, 3):
            success, msg = sign_in(token, i)
            myprint(f"{'✅' if success else '❌'} {msg}")
            if success:
                total_success += 1
            else:
                total_fail += 1
            if i == 1:   # 两次签到之间间隔2~5秒
                time.sleep(random.uniform(2, 5))

        # 账号间稍作延迟，避免请求过快
        if idx < len(token_list):
            time.sleep(random.uniform(1, 3))

    myprint("\n========== 签到完成 ==========")
    summary = f"总账号数: {len(token_list)}，成功签到次数: {total_success}，失败次数: {total_fail}"
    myprint(summary)

    # 推送通知
    notify_user("声荐签到结果", ''.join(all_logs))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("用户中断")
    except Exception as e:
        error_msg = f"脚本运行异常: {str(e)}"
        print(error_msg)
        notify_user("声荐签到异常", error_msg)
