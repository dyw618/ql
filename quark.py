#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cron: 4 13 * * *
const $ = new Env("夸克签到");

单用户版 - 直接使用完整URL作为环境变量
抓包流程：
    ① 手机端访问抽奖页
    ② 找到 url 为 https://drive-m.quark.cn/1/clouddrive/act/growth/reward 的请求
    ③ 复制整段 URL（必须包含 kps、sign、vcode 参数）
    ④ 将 URL 填入环境变量 QUARK_COOKIE
"""

import os
import sys

import requests

try:
    from notify import send
except Exception as err:
    print(f'{err}\n❌ 加载通知服务失败~')
    send = None


def get_url():
    """获取环境变量中的完整 URL"""
    url = os.getenv("QUARK_COOKIE", "").strip()
    if not url:
        print("❌ 未添加 QUARK_COOKIE 变量")
        if send:
            send("夸克自动签到", "❌ 未添加 QUARK_COOKIE 变量")
        sys.exit(0)
    return url


def extract_params(url):
    """从 URL 中提取 kps、sign、vcode"""
    query_start = url.find('?')
    query_string = url[query_start + 1:] if query_start != -1 else ''
    params = {}
    for param in query_string.split('&'):
        if '=' in param:
            key, value = param.split('=', 1)
            params[key] = value
    return {
        'kps': params.get('kps', ''),
        'sign': params.get('sign', ''),
        'vcode': params.get('vcode', '')
    }


def convert_bytes(b):
    """字节转换为可读单位"""
    units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while b >= 1024 and i < len(units) - 1:
        b /= 1024
        i += 1
    return f"{b:.2f} {units[i]}"


def get_growth_info(param):
    """获取用户签到信息"""
    url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
    querystring = {
        "pr": "qk_clouddrive",
        "fr": "iphone",
        "kps": param.get('kps'),
        "sign": param.get('sign'),
        "vcode": param.get('vcode')
    }
    resp = requests.get(url=url, params=querystring).json()
    if resp.get("data"):
        return resp["data"]
    else:
        print(f"获取成长信息失败: {resp}")
        return None


def do_growth_sign(param):
    """执行签到"""
    url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
    querystring = {
        "pr": "qk_clouddrive",
        "fr": "iphone",
        "kps": param.get('kps'),
        "sign": param.get('sign'),
        "vcode": param.get('vcode')
    }
    data = {"sign_cyclic": True}
    resp = requests.post(url=url, json=data, params=querystring).json()
    if resp.get("data"):
        return True, resp["data"]["sign_daily_reward"]
    else:
        return False, resp.get("message", "未知错误")


def main():
    print("----------夸克网盘开始签到----------")
    url = get_url()
    param = extract_params(url)

    # 获取签到信息
    growth_info = get_growth_info(param)
    if not growth_info:
        msg = "❌ 签到异常: 获取成长信息失败"
        print(msg)
        if send:
            send("夸克自动签到", msg)
        return

    # 构建日志
    log = ""
    log += f" {'88VIP' if growth_info['88VIP'] else '普通用户'}\n"
    log += f"💾 网盘总容量：{convert_bytes(growth_info['total_capacity'])}，"
    if "sign_reward" in growth_info['cap_composition']:
        log += f"签到累计容量：{convert_bytes(growth_info['cap_composition']['sign_reward'])}\n"
    else:
        log += "签到累计容量：0 MB\n"

    if growth_info["cap_sign"]["sign_daily"]:
        log += (
            f"✅ 今日已签到+{convert_bytes(growth_info['cap_sign']['sign_daily_reward'])}，"
            f"连签进度({growth_info['cap_sign']['sign_progress']}/{growth_info['cap_sign']['sign_target']})\n"
        )
    else:
        success, result = do_growth_sign(param)
        if success:
            log += (
                f"✅ 执行签到: 今日签到+{convert_bytes(result)}，"
                f"连签进度({growth_info['cap_sign']['sign_progress'] + 1}/{growth_info['cap_sign']['sign_target']})\n"
            )
        else:
            log += f"❌ 签到异常: {result}\n"

    print(log)
    if send:
        send("夸克自动签到", log)
    print("----------夸克网盘签到完毕----------")


if __name__ == "__main__":
    main()
