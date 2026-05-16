"""
工行刷卡金天天抽自动签到

支持多账号签到
https://chp.icbc.com.cn/bmcs/api-bmcs
Cookie获取：微信小程序抓包获取 Cookie 请求头

环境变量：
- ICBC_LOTTERY_CK：签到Cookie（必填，多账号换行分隔）
- ICBC_RANDOM_DELAY：随机延迟最大秒数（可选，默认300秒）
- ICBC_ENABLE_RANDOM：是否启用随机延迟（可选，默认true）

cron: 30 9 * * *
const $ = new Env("工行刷卡金天天抽小程序");
"""
import os
import time
import random
import json
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

# 配置
CORP_ID = "2000000882"
ACT_ID = "LOT20260331140621284295"
LOTTERY_URL = f"https://chp.icbc.com.cn/bmcs/api-bmcs/v3/lott/h5/lottery?corpId={CORP_ID}"
ACTIVITY_DETAIL_URL = f"https://chp.icbc.com.cn/bmcs/api-bmcs/v3/lott/h5/getActivityDetail?corpId={CORP_ID}&actId={ACT_ID}&roccSwt=0"

MAX_RANDOM_DELAY = int(os.getenv("ICBC_RANDOM_DELAY", "300"))
ENABLE_RANDOM = os.getenv("ICBC_ENABLE_RANDOM", "true").lower() == "true"

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
        "Referer": f"https://chp.icbc.com.cn/bmcs/lottery/?corpId={CORP_ID}&actId=LPARK20250801152144809773&ver=2&isElife=true&isApp=2",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF"
    }

def lottery(cookie):
    """执行抽奖"""
    headers = get_headers(cookie)
    payload = {"actId": ACT_ID, "isApp": "2"}

    try:
        if CURL_CFI_AVAILABLE:
            response = requests.post(LOTTERY_URL, json=payload, headers=headers, timeout=30, impersonate="chrome120")
        else:
            response = requests.post(LOTTERY_URL, json=payload, headers=headers, timeout=30, verify=False)

        result = response.json()
        return result
    except Exception as e:
        return {"error": str(e), "code": -1}

def extract_reward_info(result):
    """从响应中提取奖励信息"""
    # 成功抽奖的情况
    if result.get("code") == 0:
        data = result.get("data", {})
        if data.get("returnCode") == 200000:  # 抽奖成功
            reward_name = data.get("returnMsg", "")
            # 尝试从返回消息中提取奖励
            if "获得" in reward_name:
                return "success", reward_name
            else:
                return "success", "抽奖成功，请查看奖品"
        elif data.get("returnCode") == 200004:  # 已经领取过
            return "already", data.get("returnMsg", "今日已抽奖")
        else:
            return "fail", data.get("returnMsg", "未知状态")
    elif "error" in result:
        return "error", result.get("error", "请求失败")
    else:
        return "fail", result.get("message", result.get("msg", "抽奖失败"))

def extract_uid(cookie):
    """提取uid"""
    import re
    match = re.search(r'uid=([^;]+)', cookie)
    if match:
        return match.group(1)[:20] + "..."
    return "未知"

def main():
    log_print("=" * 50)
    log_print("🏆 工行刷卡金天天抽 - 自动抽奖")
    log_print(f"活动ID: {ACT_ID}")
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
    success_count = 0
    already_count = 0
    fail_count = 0
    results = []

    for idx, cookie in enumerate(cookies, 1):
        log_print(f"\n{'=' * 40}")
        uid = extract_uid(cookie)
        log_print(f"👤 账号 {idx}/{len(cookies)} ({uid})")
        log_print(f"{'-' * 40}")

        # 执行抽奖
        result = lottery(cookie)
        log_print(f"原始响应: {json.dumps(result, ensure_ascii=False)}")

        # 解析结果
        status, msg = extract_reward_info(result)

        if status == "success":
            log_print(f"🎉 {msg}")
            success_count += 1
            results.append(f"账号{idx}: 🎉 {msg}")
        elif status == "already":
            log_print(f"⚠️ {msg}")
            already_count += 1
            results.append(f"账号{idx}: ⚠️ {msg}")
        elif status == "error":
            log_print(f"❌ 网络错误: {msg}")
            fail_count += 1
            results.append(f"账号{idx}: ❌ 网络错误")
        else:
            log_print(f"❌ {msg}")
            fail_count += 1
            results.append(f"账号{idx}: ❌ {msg}")

        # 账号间延迟
        if idx < len(cookies):
            delay = random.uniform(2, 5)
            time.sleep(delay)

    # 统计输出
    log_print(f"\n{'=' * 50}")
    log_print(f"📊 执行统计:")
    log_print(f"   总账号数: {len(cookies)}")
    log_print(f"   今日新抽奖: {success_count}")
    log_print(f"   今日已抽过: {already_count}")
    log_print(f"   失败: {fail_count}")
    log_print("=" * 50)

    # 发送通知
    if results:
        title = f"工行抽奖 | 新得{success_count} | 已抽{already_count} | 失败{fail_count}"
        content = "\n".join(results)
        send_notification(title, content)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_print(f"❌ 程序异常: {e}")
        import traceback
        log_print(traceback.format_exc())
        send_notification("工行抽奖异常", f"错误: {str(e)}")
