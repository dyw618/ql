#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
工行刷卡金天天抽 + 每日签到
支持多账号
https://chp.icbc.com.cn/bmcs/api-bmcs
Cookie获取：微信小程序抓包获取 Cookie 请求头

环境变量：
- ICBC_LOTTERY_CK：签到Cookie（必填，多账号换行分隔）
- ICBC_SIGN_ACT_ID：签到活动ID（可选，默认 LOT20260804155637971766）
- ICBC_ACT_ID：抽奖活动ID（可选，默认 LOT20260331140621284295）
- ICBC_CORP_ID：（可选，默认 2000000882）
- ICBC_RANDOM_DELAY：随机延迟最大秒数（可选，默认300秒）
- ICBC_ENABLE_RANDOM：是否启用随机延迟（可选，默认true）

cron: 31 9 * * *
const $ = new Env("工行刷卡金天天抽小程序");
"""
import os
import random
import re
import time
from datetime import datetime

# 使用 curl_cffi 模拟浏览器
try:
    from curl_cffi import requests

    CURL_CFI_AVAILABLE = True
except ImportError:
    CURL_CFI_AVAILABLE = False
    import requests
    import urllib3

    urllib3.disable_warnings()

# 通知模块
try:
    from notify import send

    NOTIFY_ENABLED = True
except ImportError:
    NOTIFY_ENABLED = False

# ---------- 配置 ----------
CORP_ID = int(os.getenv("ICBC_CORP_ID", "2000000882"))
ACT_ID = os.getenv("ICBC_ACT_ID", "LOT20260331140621284295")
SIGN_ACT_ID = os.getenv("ICBC_SIGN_ACT_ID", "LOT20260804155637971766")

LOTTERY_URL = f"https://chp.icbc.com.cn/bmcs/api-bmcs/v3/lott/h5/lottery?corpId={CORP_ID}"
SIGN_URL = f"https://chp.icbc.com.cn/bmcs/api-bmcs/h5/lotRec/signIn?corpId={CORP_ID}&signActId={SIGN_ACT_ID}"

MAX_RANDOM_DELAY = int(os.getenv("MAX_RANDOM_DELAY", "300"))
ENABLE_RANDOM = os.getenv("ICBC_ENABLE_RANDOM", "true").lower() == "true"

# 重试配置
LOTTERY_RETRY = int(os.getenv("ICBC_LOTTERY_RETRY", "2"))  # 抽奖重试次数
RETRY_INTERVAL = int(os.getenv("ICBC_RETRY_INTERVAL", "300"))  # 重试间隔（秒）
SIGN_TO_LOTTERY_DELAY = 5  # 签到后等待抽奖的秒数

# 全局日志
logs = []


def log_print(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    print(formatted_msg)
    logs.append(formatted_msg + "\n")


def random_delay():
    if not ENABLE_RANDOM:
        return
    delay = random.randint(0, MAX_RANDOM_DELAY)
    if delay > 0:
        log_print(f"⏰ 随机延迟 {delay} 秒后开始")
        for remaining in range(delay, 0, -10):
            if remaining <= 30 or remaining % 30 == 0:
                log_print(f"⏳ 倒计时: {remaining} 秒")
            time.sleep(min(10, remaining))


def send_notification(title, content):
    if NOTIFY_ENABLED:
        try:
            send(title, content)
            log_print("✅ 通知发送成功")
        except Exception as e:
            log_print(f"❌ 通知发送失败: {e}")
    else:
        log_print(f"📢 {title}\n{content}")


def get_headers(cookie):
    """获取请求头"""
    return {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json; charset=UTF-8",
        "Cookie": cookie,
        "Host": "chp.icbc.com.cn",
        "Origin": "https://chp.icbc.com.cn",
        "Referer": f"https://chp.icbc.com.cn/bmcs/lottery/?corpId={CORP_ID}&actId=LPARK20250801152144809773&ver=2&isElife=true&isApp=2&encid=Uns/OyaQv6pN97djTslnmdBb4hSZmzmZ/vOFSWF4zdE=",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF"
    }


# ---------- 抽奖相关 ----------
def lottery(cookie):
    """执行抽奖"""
    headers = get_headers(cookie)
    payload = {"actId": ACT_ID, "isApp": "2"}
    try:
        if CURL_CFI_AVAILABLE:
            response = requests.post(LOTTERY_URL, json=payload, headers=headers, timeout=30, impersonate="chrome120")
        else:
            response = requests.post(LOTTERY_URL, json=payload, headers=headers, timeout=30, verify=False)
        return response.json()
    except Exception as e:
        return {"error": str(e), "code": -1}


def lottery_with_retry(cookie):
    """
    带重试机制的抽奖：
    若返回 already（已领取），等待后重试，最多 LOTTERY_RETRY 次
    返回 (status, msg, reward_detail, attempts)
    """
    last_status = last_msg = last_reward = None
    for attempt in range(1, LOTTERY_RETRY + 1):
        result = lottery(cookie)
        status, msg, reward_detail = extract_reward_info(result)
        last_status, last_msg, last_reward = status, msg, reward_detail

        if status == "already" and attempt < LOTTERY_RETRY:
            log_print(f"⚠️ 第 {attempt} 次尝试显示已领取，等待 {RETRY_INTERVAL} 秒后重试...")
            time.sleep(RETRY_INTERVAL)
            continue
        else:
            return status, msg, reward_detail, attempt

    return last_status, last_msg, last_reward, LOTTERY_RETRY


def parse_reward_detail(inner_data):
    """
    从 inner_data 中解析奖励详情
    :param inner_data: 包含 goodsSimpleName、msg、subPrizeList 的字典
    :return: 奖励描述字符串
    """
    goods_name = inner_data.get("goodsSimpleName", "")
    prize_msg = inner_data.get("msg", "")
    sub_prizes = inner_data.get("subPrizeList", [])

    if sub_prizes:
        rewards = []
        for prize in sub_prizes:
            prize_name = prize.get("goodsSimpleName", "")
            prize_num = prize.get("prizeNums", 1)
            rewards.append(f"{prize_name} x{prize_num}")
        return " + ".join(rewards)
    else:
        return prize_msg or goods_name or "获得奖励"


def extract_reward_info(result):
    """
    从响应中提取奖励信息
    返回: (status, message, reward_detail)
    status: success/already/fail/error
    """
    # 网络错误
    if "error" in result:
        return "error", result.get("error", "请求失败"), None

    # API返回错误
    if result.get("code") != 0:
        return "fail", result.get("message", result.get("msg", "抽奖失败")), None

    data = result.get("data", {})

    # 检查 suc 标识
    if data.get("suc"):
        reward_detail = parse_reward_detail(data.get("data", {}))
        return "success", "抽奖成功", reward_detail

    # 检查 returnCode
    return_code = data.get("returnCode")
    return_msg = data.get("returnMsg", "")

    if return_code == 200004:  # 已经领取过
        return "already", return_msg or "今日已抽奖", None
    elif return_code == 0:  # 新版成功标志
        reward_detail = parse_reward_detail(data.get("data", {}))
        return "success", "抽奖成功", reward_detail
    elif return_code == 200000:  # 旧版成功标志
        reward_detail = return_msg or "获得奖励"
        if "获得" in reward_detail:
            reward_detail = reward_detail.replace("获得", "")
        return "success", "抽奖成功", reward_detail
    elif return_code == 200005:  # 活动未开始或已结束
        return "fail", return_msg or "活动未开始或已结束", None
    elif return_code == 200006:  # 已达上限
        return "already", return_msg or "已达抽奖上限", None
    else:
        return "fail", return_msg or f"未知状态(code:{return_code})", None


# ---------- 工具 ----------
def extract_uid(cookie):
    """提取uid用于显示"""
    match = re.search(r'uid=([^;]+)', cookie)
    if match:
        uid = match.group(1)
        return uid[:15] + "..." if len(uid) > 20 else uid
    match = re.search(r'personId=([^;]+)', cookie)
    if match:
        pid = match.group(1)
        return pid[:15] + "..." if len(pid) > 20 else pid
    return "未知"


def format_reward_message(reward_detail):
    """格式化抽奖奖励消息"""
    if not reward_detail:
        return ""
    if "刷卡金" in reward_detail:
        amount_match = re.search(r'(\d+\.?\d*)元', reward_detail)
        if amount_match:
            return f"💰 {reward_detail}"
        return f"🎁 {reward_detail}"
    elif "微信立减金" in reward_detail or "立减金" in reward_detail:
        return f"💳 {reward_detail}"
    elif "积分" in reward_detail:
        return f"⭐ {reward_detail}"
    else:
        return f"🎁 {reward_detail}"


# ---------- 签到相关 ----------
def sign_in(cookie):
    """执行签到"""
    headers = get_headers(cookie)
    try:
        if CURL_CFI_AVAILABLE:
            response = requests.get(SIGN_URL, headers=headers, timeout=30, impersonate="chrome120")
        else:
            response = requests.get(SIGN_URL, headers=headers, timeout=30, verify=False)
        return response.json()
    except Exception as e:
        return {"error": str(e), "code": -1}


def extract_sign_info(result):
    """解析签到响应"""
    if "error" in result:
        return "error", result.get("error", "请求失败"), None
    if result.get("code") != 0:
        return "fail", result.get("message", "签到失败"), None

    data = result.get("data", {})
    error_code = data.get("errorCode")
    if error_code == 0:
        streak = data.get("streakSignDay", 0)
        return "success", f"签到成功，连续签到 {streak} 天", streak
    else:
        err_msg = data.get("errorMsg") or "签到失败"
        return "fail", err_msg, None


# ---------- 主流程 ----------
def main():
    log_print("=" * 50)
    log_print("🏆 工行刷卡金天天抽 + 每日签到")
    log_print(f"抽奖活动ID: {ACT_ID}")
    log_print(f"签到活动ID: {SIGN_ACT_ID}")
    log_print(f"随机延迟: {'开启' if ENABLE_RANDOM else '关闭'}")
    log_print(f"抽奖重试: 最多 {LOTTERY_RETRY} 次，间隔 {RETRY_INTERVAL} 秒")
    log_print("=" * 50)

    # 随机延迟
    random_delay()

    # 获取Cookie
    cookie_str = os.getenv("ICBC_LOTTERY_CK", "").strip()
    if not cookie_str:
        log_print("❌ 未找到环境变量 ICBC_LOTTERY_CK")
        send_notification("工行抽奖失败", "未配置Cookie环境变量")
        return

    cookies = [c.strip() for c in cookie_str.replace('\r\n', '\n').split('\n') if c.strip()]
    log_print(f"📋 检测到 {len(cookies)} 个账号")

    # 统计
    sign_success = 0
    sign_fail = 0
    lottery_success = 0
    lottery_already = 0
    lottery_fail = 0
    sign_results = []
    lottery_results = []
    success_rewards = []

    for idx, cookie in enumerate(cookies, 1):
        log_print(f"\n{'=' * 40}")
        uid = extract_uid(cookie)
        log_print(f"👤 账号 {idx}/{len(cookies)} ({uid})")
        log_print(f"{'-' * 40}")

        # 1. 签到
        log_print("📝 执行签到...")
        sign_resp = sign_in(cookie)
        sign_status, sign_msg, streak = extract_sign_info(sign_resp)
        if sign_status == "success":
            log_print(f"✅ {sign_msg}")
            sign_success += 1
            sign_results.append(f"账号{idx}: ✅ {sign_msg}")
        else:
            log_print(f"❌ 签到失败: {sign_msg}")
            sign_fail += 1
            sign_results.append(f"账号{idx}: ❌ {sign_msg}")

        # 签到后短暂延迟，等待服务端状态同步
        log_print(f"⏳ 等待 {SIGN_TO_LOTTERY_DELAY} 秒后开始抽奖...")
        time.sleep(SIGN_TO_LOTTERY_DELAY)

        # 2. 抽奖（带重试）
        log_print("🎰 执行抽奖...")
        lot_status, lot_msg, reward_detail, attempts = lottery_with_retry(cookie)

        if lot_status == "success":
            reward_text = format_reward_message(reward_detail) if reward_detail else f"🎉 {lot_msg}"
            retry_note = f"（第{attempts}次尝试）" if attempts > 1 else ""
            log_print(f"✅ {reward_text} {retry_note}")
            lottery_success += 1
            lottery_results.append(f"账号{idx}: ✅ {reward_text} {retry_note}")
            if reward_detail:
                success_rewards.append(f"账号{idx}: {reward_detail}")
            else:
                success_rewards.append(f"账号{idx}: 抽奖成功")
        elif lot_status == "already":
            log_print(f"⚠️ {lot_msg}（已重试{attempts}次）")
            lottery_already += 1
            lottery_results.append(f"账号{idx}: ⚠️ {lot_msg}")
        elif lot_status == "error":
            log_print(f"❌ 抽奖网络错误: {lot_msg}")
            lottery_fail += 1
            lottery_results.append(f"账号{idx}: ❌ 网络错误")
        else:
            log_print(f"❌ 抽奖失败: {lot_msg}")
            lottery_fail += 1
            lottery_results.append(f"账号{idx}: ❌ {lot_msg}")

        # 账号间延迟
        if idx < len(cookies):
            time.sleep(random.uniform(2, 5))

    # 统计输出
    log_print(f"\n{'=' * 50}")
    log_print(f"📊 执行统计:")
    log_print(f"   总账号数: {len(cookies)}")
    log_print(f"   ✅ 签到成功: {sign_success} | ❌ 签到失败: {sign_fail}")
    log_print(f"   ✅ 抽奖成功: {lottery_success} | ⚠️ 已抽过: {lottery_already} | ❌ 失败: {lottery_fail}")

    if success_rewards:
        log_print(f"\n🎁 抽奖获得奖励:")
        for reward in success_rewards:
            log_print(f"   {reward}")

    log_print("=" * 50)

    # 发送通知
    if sign_results or lottery_results:
        if sign_success > 0 or lottery_success > 0:
            title = f"🎉 工行任务完成 | 签到{sign_success} 抽奖{lottery_success}"
        elif sign_fail > 0 and lottery_fail > 0:
            title = f"❌ 工行任务失败 | 签到{sign_fail} 抽奖{lottery_fail}"
        else:
            title = f"⚠️ 工行任务 | 签到{sign_success} 抽奖{lottery_already}"

        content_lines = [f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                         f"📊 签到: 成功{sign_success} 失败{sign_fail}",
                         f"📊 抽奖: 成功{lottery_success} 已抽{lottery_already} 失败{lottery_fail}"]

        if success_rewards:
            content_lines.append(f"\n🎁 抽奖奖励:")
            for reward in success_rewards:
                content_lines.append(f"  {reward}")

        content_lines.append(f"\n📝 签到详情:")
        for r in sign_results:
            content_lines.append(f"  {r}")

        content_lines.append(f"\n📝 抽奖详情:")
        for r in lottery_results:
            content_lines.append(f"  {r}")

        content = "\n".join(content_lines)
        send_notification(title, content)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_print(f"❌ 程序异常: {e}")
        import traceback
        log_print(traceback.format_exc())
        send_notification("工行抽奖异常", f"错误: {str(e)}")
