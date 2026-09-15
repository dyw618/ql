#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cron: 8 12 * * *
const $ = new Env("BREO");

抓包breoplus.breo.cn的域名下的token，多账号换行分割
账号变量名:BREO
"""

import json
import os
import time

import requests

# ---------- 统一通知模块加载 ----------
has_notify = False
try:
    from notify import send

    has_notify = True
    print("✅ 已加载 notify.py 通知模块")
except ImportError:
    print("⚠️ 未找到 notify.py，通知功能将不可用")

# ---------- 日志收集 ----------
all_logs = []


def myprint(msg):
    """收集并打印日志"""
    print(msg)
    all_logs.append(str(msg) + "\n")


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


def get_random_one_word():
    try:
        response = requests.get("https://v1.hitokoto.cn", timeout=5)
        if response.status_code == 200:
            return response.json().get("hitokoto", "今日一言不可得")
        return "愿你每天都进步一点点"
    except Exception as e:
        myprint(f"一言接口异常: {e}")
        return "心之所向，素履以往"

def post_to_breo(token, content, title):
    """发帖，成功返回 post_id，失败返回 None"""
    url = "https://breoplus.breo.cn/breo-app/communityBaseInfo/releasePost"
    headers = {
        "token": token,
        "device-type": "Xiaomi",
        "device-version": "10",
        "channel": "Breo",
        "version_code": "30201",
        "version": "3.2.1",
        "encrypt": "1",
        "Content-Type": "application/json; charset=UTF-8"
    }
    data = {
        "anonymoused": 1,
        "content": content,
        "expressText": "",
        "images": [],
        "subTitle": "",
        "title": title,
        "topicText": ""
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                myprint("✅ 发帖成功！")
                myprint(f"帖子 ID: {result['result']['id']}")
                myprint(f"帖子标题: {result['result']['title']}")
                return result["result"]["id"]
            else:
                myprint(f"❌ 发帖失败，错误信息：{result.get('message', '未知错误')}")
                return None
        else:
            myprint(f"❌ 请求失败，状态码：{response.status_code}")
            return None
    except Exception as e:
        myprint(f"❌ 请求错误: {e}")
        return None


def collect_post(token, post_id):
    """收藏，返回 True/False"""
    url = "https://breoplus.breo.cn/breo-app/communityBaseInfo/collect"
    headers = {
        "token": token,
        "device-type": "Xiaomi",
        "device-version": "10",
        "channel": "Breo",
        "version_code": "30201",
        "version": "3.2.1",
        "encrypt": "1",
        "Content-Type": "application/json; charset=UTF-8"
    }
    data = {"postId": post_id}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                myprint("✅ 收藏成功！")
                myprint(f"获得点数: {result['result']['point']}")
                myprint(f"成长值: {result['result']['grow']}")
                return True
            else:
                myprint(f"❌ 收藏失败，错误信息：{result.get('message', '未知错误')}")
                return False
        else:
            myprint(f"❌ 请求失败，状态码：{response.status_code}")
            return False
    except Exception as e:
        myprint(f"❌ 请求错误: {e}")
        return False


def comment_post(token, post_id):
    """评论两次，返回 True/False"""
    for i in range(2):
        comment_content = get_random_one_word()
        url = "https://breoplus.breo.cn/breo-app/communityBaseInfo/comment"
        headers = {
            "token": token,
            "device-type": "Xiaomi",
            "device-version": "10",
            "channel": "Breo",
            "version_code": "30201",
            "version": "3.2.1",
            "encrypt": "1",
            "Content-Type": "application/json; charset=UTF-8"
        }
        data = {
            "anonymoused": 0,
            "commentText": comment_content,
            "postId": post_id
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    myprint(f"✅ 第{i + 1}次评论成功！")
                    myprint(f"评论内容: {result['result']['rootOutVO']['commentText']}")
                    myprint(f"获得点数: {result['result']['point']}")
                    myprint(f"成长值: {result['result']['grow']}")
                else:
                    myprint(f"❌ 评论失败，错误信息：{result.get('message', '未知错误')}")
                    return False
            else:
                myprint(f"❌ 请求失败，状态码：{response.status_code}")
                return False
        except Exception as e:
            myprint(f"❌ 请求错误: {e}")
            return False
        time.sleep(1)
    return True


def browse_mall(token):
    """浏览商城，返回 True/False"""
    url = "https://breoplus.breo.cn/breo-app/user/po-task-info/mall"
    headers = {
        "token": token,
        "device-type": "Xiaomi",
        "device-version": "10",
        "channel": "Breo",
        "version_code": "30201",
        "version": "3.2.1",
        "encrypt": "1"
    }
    try:
        response = requests.post(url, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                myprint("✅ 浏览商城成功！")
                myprint(f"获得点数: {result['result']['point']}")
                myprint(f"成长值: {result['result']['grow']}")
                return True
            else:
                myprint(f"❌ 浏览商城失败，错误信息：{result.get('message', '未知错误')}")
                return False
        else:
            myprint(f"❌ 请求失败，状态码：{response.status_code}")
            return False
    except Exception as e:
        myprint(f"❌ 请求错误: {e}")
        return False


def punch_in(token):
    """签到，返回 True/False"""
    url = "https://breoplus.breo.cn/breo-app/user/po-task-info/punch"
    headers = {
        "Host": "breoplus.breo.cn",
        "Connection": "keep-alive",
        "Content-Length": "0",
        "content-type": "application/json",
        "token": token,
        "charset": "utf-8",
        "Referer": "https://servicewechat.com/wx61457400e4212cec/304/page-frame.html",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; MI 8 Build/QKQ1.190828.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/134.0.6998.136 Mobile Safari/537.36 XWEB/1340043 MMWEBSDK/20241202 MMWEBID/3628 MicroMessenger/8.0.56.2800(0x2800385E) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 MiniProgramEnv/android",
        "Accept-Encoding": "gzip, deflate, br"
    }
    try:
        response = requests.post(url, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                myprint("✅ 签到成功！")
                myprint(f"获得点数: {result['result']['point']}")
                myprint(f"成长值: {result['result']['grow']}")
                return True
            else:
                myprint(f"❌ 签到失败，错误信息：{result.get('message', '未知错误')}")
                return False
        else:
            myprint(f"❌ 请求失败，状态码：{response.status_code}")
            return False
    except Exception as e:
        myprint(f"❌ 请求错误: {e}")
        return False


# ---------- 单账号任务 ----------
def run_account(token, idx):
    """
    执行单个账号的完整任务流
    签到失败则跳过后续操作
    """
    myprint(f"\n-------------- 账号 {idx} 开始 --------------")

    # 1. 签到
    myprint("🚀 正在签到...")
    if not punch_in(token):
        myprint("⛔ 签到失败，跳过该账号后续操作")
        myprint(f"-------------- 账号 {idx} 结束 --------------")
        return

    # 2. 发帖
    myprint("\n📝 正在发布帖子...")
    post_id = post_to_breo(token, "这是一个自动发布的帖子", "自动化测试")
    if not post_id:
        myprint("⛔ 发帖失败，跳过后续操作")
        myprint(f"-------------- 账号 {idx} 结束 --------------")
        return

    # 3. 收藏
    myprint("\n⭐ 正在收藏帖子...")
    if not collect_post(token, post_id):
        myprint("⚠️ 收藏失败，继续后续操作")

    # 4. 评论
    myprint("\n💬 正在评论帖子...")
    if not comment_post(token, post_id):
        myprint("⚠️ 评论失败，继续后续操作")

    # 5. 浏览商城
    myprint("\n🛒 正在浏览商城...")
    browse_mall(token)

    myprint(f"-------------- 账号 {idx} 结束 --------------")


if __name__ == "__main__":
    try:
        # 从环境变量读取 token
        tokens = os.getenv("BREO", "").splitlines()

        if not tokens:
            myprint("❌ 未检测到账号信息（环境变量 BREO），退出脚本。")
            notify_user("BREO任务失败", "未检测到账号信息（环境变量 BREO）")
        else:
            myprint("=开始执行任务=")
            for i, token in enumerate(tokens, 1):
                if token.strip():
                    run_account(token.strip(), i)

            myprint("\n=所有任务执行完毕=")

        # 发送通知
        notify_user("BREO小程序签到", ''.join(all_logs))

    except Exception as e:
        error_msg = f"脚本运行异常: {str(e)}"
        myprint(error_msg)
        notify_user("BREO任务异常", error_msg)
