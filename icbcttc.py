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

MAX_RANDOM_DELAY = int(os.getenv("MAX_RANDOM_DELAY", "300"))
ENABLE_RANDOM = os.getenv("ICBC_ENABLE_RANDOM", "false").lower() == "true"

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
    if data.get("suc") == True:
        # 获取详细奖励信息
        inner_data = data.get("data", {})
        goods_name = inner_data.get("goodsSimpleName", "")
        prize_msg = inner_data.get("msg", "")

        # 解析子奖品列表
        sub_prizes = inner_data.get("subPrizeList", [])
        if sub_prizes:
            rewards = []
            for prize in sub_prizes:
                prize_name = prize.get("goodsSimpleName", "")
                prize_num = prize.get("prizeNums", 1)
                rewards.append(f"{prize_name} x{prize_num}")
            reward_detail = " + ".join(rewards)
        else:
            reward_detail = prize_msg or goods_name or "获得奖励"

        return "success", "抽奖成功", reward_detail

    # 检查 returnCode
    return_code = data.get("returnCode")
    return_msg = data.get("returnMsg", "")

    if return_code == 200004:  # 已经领取过
        return "already", return_msg or "今日已抽奖", None
    elif return_code == 0:  # 新版成功标志
        # 从 data.data 中获取奖励
        inner_data = data.get("data", {})
        goods_name = inner_data.get("goodsSimpleName", "")
        prize_msg = inner_data.get("msg", "")

        # 解析子奖品
        sub_prizes = inner_data.get("subPrizeList", [])
        if sub_prizes:
            rewards = []
            for prize in sub_prizes:
                prize_name = prize.get("goodsSimpleName", "")
                prize_num = prize.get("prizeNums", 1)
                rewards.append(f"{prize_name} x{prize_num}")
            reward_detail = " + ".join(rewards)
        else:
            reward_detail = prize_msg or goods_name or "获得奖励"

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

def extract_uid(cookie):
    """提取uid"""
    import re
    match = re.search(r'uid=([^;]+)', cookie)
    if match:
        uid = match.group(1)
        if len(uid) > 20:
            return uid[:15] + "..."
        return uid
    # 尝试提取其他标识
    match = re.search(r'personId=([^;]+)', cookie)
    if match:
        pid = match.group(1)
        if len(pid) > 20:
            return pid[:15] + "..."
        return pid
    return "未知"

def format_reward_message(reward_detail):
    """格式化奖励消息"""
    if not reward_detail:
        return ""

    # 处理不同的奖励格式
    if "刷卡金" in reward_detail:
        # 提取金额
        import re
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

def main():
    log_print("=" * 50)
    log_print("🏆 工行刷卡金天天抽 - 自动抽奖")
    log_print(f"活动ID: {ACT_ID}")
    log_print(f"随机延迟: {'开启' if ENABLE_RANDOM else '关闭'}")
    if ENABLE_RANDOM:
        log_print(f"最大延迟: {MAX_RANDOM_DELAY}秒")
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
    success_rewards = []  # 记录成功获得的奖励

    for idx, cookie in enumerate(cookies, 1):
        log_print(f"\n{'=' * 40}")
        uid = extract_uid(cookie)
        log_print(f"👤 账号 {idx}/{len(cookies)} ({uid})")
        log_print(f"{'-' * 40}")

        # 执行抽奖
        result = lottery(cookie)

        # 调试：打印完整响应（可选，去掉注释可查看）
        # log_print(f"原始响应: {json.dumps(result, ensure_ascii=False)}")

        # 解析结果
        status, msg, reward_detail = extract_reward_info(result)

        if status == "success":
            reward_text = format_reward_message(reward_detail) if reward_detail else f"🎉 {msg}"
            log_print(f"✅ {reward_text}")
            success_count += 1
            results.append(f"账号{idx}: ✅ {reward_text}")
            if reward_detail:
                success_rewards.append(f"账号{idx}: {reward_detail}")
            else:
                success_rewards.append(f"账号{idx}: 抽奖成功")
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
    log_print(f"   ✅ 抽奖成功: {success_count}")
    log_print(f"   ⚠️ 今日已抽过: {already_count}")
    log_print(f"   ❌ 失败: {fail_count}")

    if success_rewards:
        log_print(f"\n🎁 获得奖励:")
        for reward in success_rewards:
            log_print(f"   {reward}")

    log_print("=" * 50)

    # 发送通知
    if results:
        # 构建通知标题
        if success_count > 0:
            title = f"🎉 工行抽奖成功 | 获得{success_count}个奖励"
        elif already_count > 0:
            title = f"⚠️ 工行抽奖 | 已抽{already_count}个"
        else:
            title = f"❌ 工行抽奖失败 | 失败{fail_count}个"

        # 构建通知内容
        content_lines = []
        content_lines.append(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content_lines.append(f"📊 统计: 成功{success_count} | 已抽{already_count} | 失败{fail_count}")

        if success_rewards:
            content_lines.append(f"\n🎁 获得奖励:")
            for reward in success_rewards:
                content_lines.append(f"  {reward}")

        content_lines.append(f"\n📝 详细结果:")
        for result in results:
            content_lines.append(f"  {result}")

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
