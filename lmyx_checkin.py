#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
老木社区 每日签到
cron: 13 13 * * *
const $ = new Env("老木社区签到");

环境变量：
    lmyx_CK   - 必填，从抓包中获取的 Cookie 字符串（完整复制）
    lmyx_URL  - 可选，自定义主签到域名（如 "laomuxs.cn" 或 "https://laomuxs.cn"），
                默认为 "https://laomuxs.cn"，若失败则自动切换至备用域名 "https://laomu.yyqzx.com"
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


# ---------- 签到函数（支持指定 base_url） ----------
def sign_in(cookie, base_url):
    """
    执行签到请求
    :param cookie: 完整的 Cookie 字符串
    :param base_url: 基础域名（如 "https://laomuxs.cn"）
    :return: (success, message, detail)
    """
    url = f"{base_url}/wp-admin/admin-ajax.php"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate",  # 移除 br 和 zstd
        "Accept-Language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie,
        "Host": base_url.replace("https://", "").replace("http://", ""),  # 提取 Host
        "Origin": base_url,
        "Referer": f"{base_url}/",
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
            # 签到成功
            msg = resp_json.get("msg", "")
            points = resp_json.get("data", {}).get("points", 0)
            integral = resp_json.get("data", {}).get("integral", 0)
            continuous = resp_json.get("continuous_day", 0)
            detail = f"连续签到 {continuous} 天，获得积分 {points}，经验 {integral}"
            return True, msg, detail
        else:
            err = resp_json.get("msg", "未知错误")
            # 检查是否表示已签到
            if "已签到" in err or "已签" in err:
                # 视为签到成功（今日已签），提取现有数据
                msg = err
                points = resp_json.get("data", {}).get("points", 0)
                integral = resp_json.get("data", {}).get("integral", 0)
                continuous = resp_json.get("continuous_day", 0)
                detail = f"（今日已签到）连续签到 {continuous} 天，已获积分 {points}，经验 {integral}"
                return True, msg, detail
            else:
                return False, f"签到失败: {err}", ""

    except requests.exceptions.RequestException as e:
        # 网络异常（包括超时、连接错误等）
        return False, f"网络异常: {str(e)}", ""
    except Exception as e:
        return False, f"请求异常: {str(e)}", ""


# ---------- 主函数（含重试和 URL 切换） ----------
def main():
    cookie = os.getenv("lmyx_CK")
    if not cookie:
        print("❌ 未设置环境变量 lmyx_CK")
        send_notify("老木社区签到失败", "未设置环境变量 lmyx_CK")
        sys.exit(1)

    # 获取自定义主域名，若未设置则使用默认
    custom_url = os.getenv("lmyx_URL", "").strip()
    if custom_url:
        if not custom_url.startswith(("http://", "https://")):
            custom_url = "https://" + custom_url
        primary_base = custom_url
    else:
        primary_base = "https://laomuxs.cn"

    backup_base = "https://laomu.yyqzx.com"  # 固定备用域名

    # 按顺序尝试的域名列表
    url_list = [primary_base, backup_base]

    max_retries = 3  # 每个域名最大重试次数（仅对网络错误）
    retry_interval = 60  # 1 分钟

    # 循环尝试不同域名
    for idx, base_url in enumerate(url_list):
        print(f"\n🌐 尝试域名 [{idx + 1}/{len(url_list)}]: {base_url}")
        for attempt in range(1, max_retries + 1):
            print(f"   尝试 {attempt}/{max_retries}...")
            success, msg, detail = sign_in(cookie.strip(), base_url)

            if success:
                print(f"✅ {msg}")
                print(f"📊 {detail}")
                send_notify("老木社区签到结果", f"{msg}\n{detail}")
                return  # 成功则直接退出

            # 失败处理
            print(f"   ❌ {msg}")

            # 判断是否为网络超时/连接错误（可重试）
            error_lower = msg.lower()
            is_timeout = any(kw in error_lower for kw in ["timeout", "timed out", "connection"])

            if is_timeout and attempt < max_retries:
                print(f"   ⏰ 网络超时，等待 {retry_interval // 60} 分钟后重试...")
                time.sleep(retry_interval)
                continue
            else:
                # 非网络错误 或 已达重试上限，跳出当前域名的重试循环，尝试下一个域名
                print(f"   ❌ 当前域名失败，切换至下一个域名")
                break

        # 若所有重试均失败，尝试下一个域名
    else:
        # 所有域名均尝试失败
        print("❌ 所有域名均签到失败")
        send_notify("老木社区签到失败", "所有域名均签到失败，请检查网络或 Cookie")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"脚本异常: {e}")
        send_notify("老木社区签到异常", str(e))
