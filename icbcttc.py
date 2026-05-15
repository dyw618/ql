"""
工行刷卡金天天抽自动签到

支持多账号签到
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

# 使用 curl_cffi 替代 requests
try:
    from curl_cffi import requests
    CURL_CFI_AVAILABLE = True
except ImportError:
    CURL_CFI_AVAILABLE = False
    import requests
    import urllib3
    urllib3.disable_warnings()

try:
    from notify import send
    NOTIFY_ENABLED = True
except ImportError:
    NOTIFY_ENABLED = False

CORP_ID = "2000000882"
ACT_ID = "LOT20260331140621284295"
SIGN_URL = f"https://chp.icbc.com.cn/bmcs/api-bmcs/v3/lott/h5/lottery?corpId={CORP_ID}"

logs = []

def log_print(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    print(formatted_msg)
    logs.append(formatted_msg + "\n")

def sign_in(cookie):
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json; charset=UTF-8",
        "Cookie": cookie,
        "Host": "chp.icbc.com.cn",
        "Origin": "https://chp.icbc.com.cn",
        "Referer": f"https://chp.icbc.com.cn/bmcs/lottery/?corpId={CORP_ID}&actId=LPARK20250801152144809773&ver=2&isElife=true&isApp=2",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }
    payload = {"actId": ACT_ID, "isApp": "2"}
    
    try:
        if CURL_CFI_AVAILABLE:
            # 使用 curl_cffi 模拟 Chrome 浏览器
            response = requests.post(
                SIGN_URL, 
                json=payload, 
                headers=headers, 
                timeout=30,
                impersonate="chrome120"  # 模拟 Chrome 120 的指纹
            )
        else:
            # 降级使用普通 requests
            log_print("⚠️ curl_cffi未安装，使用普通模式（可能失败）")
            response = requests.post(
                SIGN_URL, 
                json=payload, 
                headers=headers, 
                timeout=30, 
                verify=False
            )
        
        result = response.json()
        log_print(f"响应: {json.dumps(result, ensure_ascii=False)}")
        
        if result.get("code") == 0 or result.get("success"):
            # 尝试获取奖励信息
            msg = "签到成功"
            data = result.get("data", {})
            if data.get("rewardName"):
                msg += f"，获得 {data.get('rewardName')}"
            if data.get("point"):
                msg += f"，获得 {data.get('point')} 积分"
            return True, msg
        else:
            err_msg = result.get("message") or result.get("msg") or "签到失败"
            return False, err_msg
            
    except Exception as e:
        return False, f"错误: {str(e)}"

def main():
    log_print("=" * 50)
    log_print("🚀 工行签到脚本启动")
    if CURL_CFI_AVAILABLE:
        log_print("✅ 使用 curl_cffi 模式")
    else:
        log_print("⚠️ 使用普通模式，建议安装 curl_cffi: pip install curl_cffi")
    log_print("=" * 50)
    
    cookie_str = os.getenv("ICBC_LOTTERY_CK", "").strip()
    if not cookie_str:
        log_print("❌ 未找到环境变量 ICBC_LOTTERY_CK")
        return
    
    cookies = [c.strip() for c in cookie_str.replace('\r\n', '\n').split('\n') if c.strip()]
    log_print(f"检测到 {len(cookies)} 个账号")
    
    results = []
    for idx, cookie in enumerate(cookies, 1):
        log_print(f"\n处理账号 {idx}")
        success, msg = sign_in(cookie)
        if success:
            log_print(f"✅ {msg}")
            results.append(f"账号{idx}: ✅ {msg}")
        else:
            log_print(f"❌ {msg}")
            results.append(f"账号{idx}: ❌ {msg}")
        time.sleep(random.uniform(2, 5))
    
    if NOTIFY_ENABLED and results:
        send("工行签到", "\n".join(results))

if __name__ == "__main__":
    main()
