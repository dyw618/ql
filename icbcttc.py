"""
工行刷卡金天天抽自动签到

支持多账号签到
Cookie获取：微信小程序抓包获取 Cookie 请求头

环境变量：
- ICBC_LOTTERY_CK：签到Cookie（必填，多账号换行分隔）
- ICBC_RANDOM_DELAY：随机延迟最大秒数（可选，默认300秒）
- ICBC_ENABLE_RANDOM：是否启用随机延迟（可选，默认true）

cron: 55 9 * * *
"""
import requests
import os
import time
import random
import json
from datetime import datetime

# ------------------ 通知模块 ------------------
try:
    from notify import send
    NOTIFY_ENABLED = True
    print("✅ 通知模块加载成功")
except ImportError:
    NOTIFY_ENABLED = False
    print("⚠️ 未找到通知模块，将不发送通知")

# ------------------ 配置 ------------------
CORP_ID = "2000000882"
ACT_ID = "LOT20260331140621284295"
SIGN_URL = f"https://chp.icbc.com.cn/bmcs/api-bmcs/v3/lott/h5/lottery?corpId={CORP_ID}"

# 随机延迟配置（默认最大延迟300秒，避免并发）
MAX_RANDOM_DELAY = int(os.getenv("ICBC_RANDOM_DELAY", "300"))
ENABLE_RANDOM = os.getenv("ICBC_ENABLE_RANDOM", "true").lower() == "true"

# 请求头（固定部分）
BASE_HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/json; charset=UTF-8",
    "Host": "chp.icbc.com.cn",
    "Origin": "https://chp.icbc.com.cn",
    "Referer": f"https://chp.icbc.com.cn/bmcs/lottery/?corpId={CORP_ID}&actId=LPARK20250801152144809773&ver=2&isElife=true&isApp=2",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF"
}

# 请求体
PAYLOAD = {
    "actId": ACT_ID,
    "isApp": "2"
}

# 全局日志收集
logs = []

def log_print(msg):
    """打印并收集日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    print(formatted_msg)
    logs.append(formatted_msg + "\n")

def random_delay():
    """随机延迟"""
    if not ENABLE_RANDOM:
        return
    delay = random.randint(0, MAX_RANDOM_DELAY)
    if delay > 0:
        log_print(f"⏰ 随机延迟 {delay} 秒后开始签到")
        for remaining in range(delay, 0, -10):
            if remaining <= 30 or remaining % 30 == 0:
                log_print(f"⏳ 倒计时: {remaining} 秒")
            time.sleep(min(10, remaining))
        time.sleep(0)  # 确保剩余时间

def send_notification(title, content):
    """发送通知"""
    if NOTIFY_ENABLED:
        try:
            send(title, content)
            log_print("✅ 通知发送成功")
        except Exception as e:
            log_print(f"❌ 通知发送失败: {e}")
    else:
        log_print(f"📢 {title}\n{content}")

def sign_in(cookie):
    """
    执行签到请求
    :param cookie: 完整的Cookie字符串
    :return: (success, message, data)
    """
    headers = BASE_HEADERS.copy()
    headers["Cookie"] = cookie
    
    try:
        log_print("📡 发送签到请求...")
        response = requests.post(
            SIGN_URL,
            json=PAYLOAD,
            headers=headers,
            timeout=15
        )
        
        # 打印响应状态码
        log_print(f"响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            return False, f"HTTP错误: {response.status_code}", None
        
        # 解析响应
        result = response.json()
        log_print(f"响应数据: {json.dumps(result, ensure_ascii=False)}")
        
        # 根据实际返回判断签到结果
        # 示例中可能是 code=0 表示成功
        if result.get("code") == 0 or result.get("success") == True:
            msg = result.get("message") or result.get("msg") or "签到成功"
            # 尝试获取奖励信息
            data = result.get("data", {})
            reward_name = data.get("rewardName") or data.get("reward")
            reward_point = data.get("point") or data.get("rewardPoint")
            
            if reward_name:
                msg += f"，获得 {reward_name}"
            if reward_point:
                msg += f"，获得 {reward_point} 积分"
            
            return True, msg, result
        else:
            err_msg = result.get("message") or result.get("msg") or result.get("errorMsg") or "签到失败"
            return False, err_msg, result
            
    except requests.exceptions.Timeout:
        return False, "请求超时", None
    except requests.exceptions.RequestException as e:
        return False, f"网络异常: {str(e)}", None
    except json.JSONDecodeError:
        return False, "响应解析失败", None
    except Exception as e:
        return False, f"未知错误: {str(e)}", None

def extract_uid(cookie):
    """从Cookie中提取uid"""
    import re
    match = re.search(r'uid=([^;]+)', cookie)
    if match:
        return match.group(1)
    return "未知"

def main():
    """主函数"""
    log_print("=" * 50)
    log_print("🚀 工行刷卡金天天抽签到脚本启动")
    log_print(f"活动ID: {ACT_ID}")
    log_print(f"企业ID: {CORP_ID}")
    log_print("=" * 50)
    
    # 随机延迟
    random_delay()
    
    # 获取Cookie配置
    cookie_str = os.getenv("ICBC_LOTTERY_CK", "").strip()
    if not cookie_str:
        log_print("❌ 未找到环境变量 ICBC_LOTTERY_CK")
        log_print("请在青龙面板添加环境变量: ICBC_LOTTERY_CK")
        send_notification("工行签到失败", "未配置Cookie环境变量")
        return
    
    # 分割多账号（支持换行或分号）
    cookies = []
    for line in cookie_str.replace('\r\n', '\n').split('\n'):
        line = line.strip()
        if line:
            cookies.append(line)
    
    if not cookies:
        log_print("❌ 未找到有效的Cookie")
        return
    
    log_print(f"📋 检测到 {len(cookies)} 个账号")
    
    # 签到统计
    success_count = 0
    fail_count = 0
    results = []
    
    for idx, cookie in enumerate(cookies, 1):
        log_print(f"\n{'=' * 40}")
        uid = extract_uid(cookie)
        log_print(f"👤 账号 {idx}/{len(cookies)} (UID: {uid})")
        log_print(f"{'-' * 40}")
        
        # 执行签到
        success, msg, _ = sign_in(cookie)
        
        if success:
            log_print(f"✅ {msg}")
            success_count += 1
            results.append(f"账号{idx}({uid}): ✅ {msg}")
        else:
            log_print(f"❌ {msg}")
            fail_count += 1
            results.append(f"账号{idx}({uid}): ❌ {msg}")
        
        # 账号间延迟
        if idx < len(cookies):
            delay = random.uniform(2, 5)
            log_print(f"⏱️  等待 {delay:.1f} 秒后处理下一个账号...")
            time.sleep(delay)
    
    # 输出统计
    log_print(f"\n{'=' * 50}")
    log_print(f"📊 签到统计:")
    log_print(f"   总账号数: {len(cookies)}")
    log_print(f"   成功: {success_count}")
    log_print(f"   失败: {fail_count}")
    log_print("=" * 50)
    
    # 发送通知
    if results:
        title = f"工行签到完成 | 成功{success_count}/{len(cookies)}"
        content = "\n".join(results)
        send_notification(title, content)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_print("⚠️ 用户中断")
    except Exception as e:
        log_print(f"❌ 程序异常: {e}")
        import traceback
        log_print(traceback.format_exc())
        send_notification("工行签到异常", f"错误: {str(e)}")
    finally:
        log_print("\n🏁 脚本执行完毕")
