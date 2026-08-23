#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一步两步游戏区服常驻监测（每分钟随机间隔检测）
随机延迟范围硬编码为 1~2 分钟，如需调整请直接修改脚本中的 MIN_DELAY / MAX_DELAY。

环境变量：
    yblb_CK - 必填，完整的接口请求URL后面的参数（含所有参数，如ts、sign等）
"""

import os
import random
import sys
import time

import requests

# ---------- 通知模块加载 ----------
has_notify = False
try:
    from notify import send

    has_notify = True
    print("✅ 已加载 notify.py 通知模块")
except ImportError:
    print("⚠️ 未找到 notify.py，通知功能将不可用")


def send_notify(title, content):
    if has_notify:
        try:
            send(title, content)
            print("✅ 通知发送成功")
        except Exception as e:
            print(f"❌ 通知发送失败: {e}")
    else:
        print(f"📢 {title}\n{content}")


# ---------- 配置 ----------
MONITOR_URL = "https://rogue121-front.feiyuapi.com/front/svrlist?" + os.getenv("yblb_CK")
if not MONITOR_URL:
    print("❌ 错误：未设置环境变量 MONITOR_URL")
    sys.exit(1)

STORAGE_FILE = "yblb_max_server_id.txt"  # 存储上次最大ID的本地文件
# 随机延迟范围（秒）- 直接硬编码，不从环境变量读取
MIN_DELAY = 60
MAX_DELAY = 120
delay = random.randint(MIN_DELAY, MAX_DELAY)


# ---------- 核心函数 ----------
def get_max_server_id():
    """请求接口并返回最大区服ID及其详细信息"""
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "rogue121-front.feiyuapi.com",
        "Referer": "https://servicewechat.com/wx124633d4e9338db6/233/page-frame.html",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541a35) XWEB/25297",
        "xweb_xhr": "1"
    }
    try:
        resp = requests.get(MONITOR_URL, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        svrlist = data.get("svrlist", [])
        if not svrlist:
            return None, None
        max_id = max(item["id"] for item in svrlist)
        max_item = next((item for item in svrlist if item["id"] == max_id), None)
        return max_id, max_item
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None, None


def read_stored_max():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            content = f.read().strip()
            if content.isdigit():
                return int(content)
    return 0


def write_stored_max(value):
    with open(STORAGE_FILE, "w") as f:
        f.write(str(value))


# ---------- 主循环 ----------
def main():
    print(f"🟢 区服监测守护进程启动，随机延迟范围 {MIN_DELAY}~{MAX_DELAY} 秒")
    # 初始化存储值（首次运行直接写入当前最大值）
    first_max, _ = get_max_server_id()
    if first_max is not None:
        write_stored_max(first_max)
        print(f"📌 初始最大区服ID: {first_max}")
    else:
        print("⚠️ 首次请求失败，将使用存储值0")

    while True:
        try:
            current_max, item = get_max_server_id()
            if current_max is None:
                print("⚠️ 本次检测失败，等待下次重试")
            else:
                stored = read_stored_max()
                if current_max > stored:
                    name = item.get("name", "") if item else ""
                    content = f"🚀 新增区服！\nID: {current_max}\n名称: {name}"
                    send_notify("游戏新区服提醒", content)
                    print(content)
                    write_stored_max(current_max)
                else:
                    print(f"✅ {time.strftime('%Y-%m-%d %H:%M:%S')} 无新区服增加 (当前最大ID: {current_max})")
        except Exception as e:
            print(f"❌ 循环异常: {e}")

        # 随机延迟（固定范围，不依赖环境变量）
        delay = random.randint(MIN_DELAY, MAX_DELAY)
        print(f"⏳ 下次检测将在 {delay} 秒后...")
        time.sleep(delay)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断，脚本退出")
    except Exception as e:
        error_msg = f"脚本致命异常: {e}"
        print(error_msg)
        send_notify("区服监测异常", error_msg)
