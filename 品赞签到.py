"""
cron: 35 2 * * 1
const $ = new Env("品赞HTTP代理签到脚本");
品赞HTTP代理签到脚本
变量名: pzhttp
格式: 账号#密码，多账号用换行隔开
例如:
18888888888#a18888888888
"""
import json
import os
import random
import string

import requests

# ---------------- 统一通知模块加载 ----------------
hadsend = False
send = None
try:
    from notify import send

    hadsend = True
    print("✅ 已加载notify.py通知模块")
except ImportError:
    print("⚠️  未加载通知模块，跳过通知功能")


def notify_user(title, content):
    """统一通知函数"""
    if hadsend:
        try:
            send(title, content)
            print(f"✅ 通知发送完成: {title}")
        except Exception as e:
            print(f"❌ 通知发送失败: {e}")
    else:
        print(f"📢 {title}\n📄 {content}")


class Base64Obfuscator:
    def __init__(self):
        self.table = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789+/"
        )

    def utf16_to_utf8(self, s):
        result = []
        for char in s:
            code = ord(char)
            if 0 < code <= 127:
                result.append(char)
            elif 128 <= code <= 2047:
                byte1 = chr(192 | (code >> 6) & 31)
                byte2 = chr(128 | code & 63)
                result.extend([byte1, byte2])
            elif 2048 <= code <= 65535:
                byte1 = chr(224 | (code >> 12) & 15)
                byte2 = chr(128 | (code >> 6) & 63)
                byte3 = chr(128 | code & 63)
                result.extend([byte1, byte2, byte3])
        return ''.join(result)

    def utf8_to_utf16(self, s):
        result = []
        i = 0
        while i < len(s):
            byte = ord(s[i])
            i += 1
            if byte & 0x80 == 0:
                result.append(s[i - 1])
            elif (byte & 0xE0) == 0xC0:
                byte2 = ord(s[i])
                i += 1
                code = ((byte & 0x1F) << 6) | (byte2 & 0x3F)
                result.append(chr(code))
            elif (byte & 0xF0) == 0xE0:
                byte2 = ord(s[i])
                byte3 = ord(s[i + 1])
                i += 2
                code = ((byte & 0x0F) << 12) | ((byte2 & 0x3F) << 6) | (byte3 & 0x3F)
                result.append(chr(code))
        return ''.join(result)

    def encode(self, s):
        if not s:
            return ""

        utf8_bytes = self.utf16_to_utf8(s)
        i = 0
        result = []
        n = len(utf8_bytes)

        while i < n:
            o = ord(utf8_bytes[i])
            i += 1
            result.append(self.table[o >> 2])

            if i == n:
                result.append(self.table[(o & 3) << 4])
                result.append('==')
                break

            s_byte = ord(utf8_bytes[i])
            i += 1
            if i == n:
                result.append(self.table[(o & 3) << 4 | (s_byte >> 4) & 15])
                result.append(self.table[(s_byte & 15) << 2])
                result.append('=')
                break

            a = ord(utf8_bytes[i])
            i += 1
            result.append(self.table[(o & 3) << 4 | (s_byte >> 4) & 15])
            result.append(self.table[(s_byte & 15) << 2 | (a & 192) >> 6])
            result.append(self.table[a & 63])

        return ''.join(result)


def generate_obfuscated_account(phone, password):
    salt = "QWERIPZAN1290QWER"
    concat = phone + salt + password
    obfuscator = Base64Obfuscator()
    encoded = obfuscator.encode(concat)

    hex_chars = string.hexdigits.lower()
    t = ''.join(''.join(random.choice(hex_chars) for _ in range(12)) for _ in range(80))

    if len(t) < 400:
        t += ''.join(random.choice(hex_chars) for _ in range(400 - len(t)))
    else:
        t = t[:400]

    part1 = t[:100]
    part2 = encoded[:8]
    part3 = t[100:200]
    part4 = encoded[8:20]
    part5 = t[200:300]
    part6 = encoded[20:]
    part7 = t[300:400]

    account = part1 + part2 + part3 + part4 + part5 + part6 + part7
    return account


def login(phone, password):
    url = "https://service.ipzan.com/users-login"
    obfuscated_account = generate_obfuscated_account(phone, password)
    payload = {
        "account": obfuscated_account,
        "source": "ipzan-home-one"
    }
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
        'Accept': "application/json, text/plain, */*",
        'Content-Type': "application/json",
        'Accept-Language': "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        'Authorization': "Bearer null",
        'Content-Type': "application/json;charset=UTF-8",
        'Origin': "https://www.ipzan.com",
        'Referer': "https://www.ipzan.com/",
        'Sec-Fetch-Dest': "empty",
        'Sec-Fetch-Mode': "cors",
        'Sec-Fetch-Site': "same-site",
        'sec-ch-ua-mobile': "?0",
        'sec-ch-ua-platform': "\"Windows\"",
        'Cookie': "locale=en-us"
    }
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            token = data["data"]["token"]
            return token, "登录成功"
        else:
            msg = f"登录失败: {data.get('message', '未知错误')}"
            print(msg)
            return None, msg
    except Exception as e:
        msg = f"登录请求异常: {str(e)}"
        print(msg)
        return None, msg


def get_wallet_info(token):
    url = "https://service.ipzan.com/home/userWallet-find"
    headers = {
        'Host': 'service.ipzan.com',
        'Connection': 'keep-alive',
        'sec-ch-ua-platform': '"Windows"',
        'Authorization': f'Bearer {token}',
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
        'Accept': "application/json, text/plain, */*",
        'sec-ch-ua': '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'DNT': '1',
        'sec-ch-ua-mobile': "?0",
        'Origin': "https://www.ipzan.com",
        'Sec-Fetch-Site': "same-site",
        'Sec-Fetch-Mode': "cors",
        'Sec-Fetch-Dest': "empty",
        'Referer': "https://www.ipzan.com/",
        'Accept-Encoding': "gzip, deflate, br, zstd",
        'Accept-Language': "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            wallet_data = data.get("data", {})
            balance = wallet_data.get("balance", 0)
            bonus_amount = wallet_data.get("bonus_amount", 0)
            real_amount = wallet_data.get("real_amount", 0)
            levelReward = wallet_data.get("levelReward", False)
            print(f"💰 当前余额: {balance}")
            print(f"🎁 奖励金额: {bonus_amount}")
            print(f"💵 真实金额: {real_amount}")
            if levelReward:
                print(f"🏆 可领取等级奖励")
            return wallet_data, f"余额:{balance},奖励:{bonus_amount},实额:{real_amount}"
        else:
            msg = f"查询余额失败: {data.get('message', '未知错误')}"
            print(msg)
            return None, msg
    except Exception as e:
        msg = f"查询余额异常: {str(e)}"
        print(msg)
        return None, msg


def sign_in(token):
    url = "https://service.ipzan.com/home/userWallet-receive"
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
        'Accept': "application/json, text/plain, */*",
        'Accept-Language': "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        'Authorization': f"Bearer {token}",
        'Origin': "https://www.ipzan.com",
        'Referer': "https://www.ipzan.com/",
        'Sec-Fetch-Dest': "empty",
        'Sec-Fetch-Mode': "cors",
        'Sec-Fetch-Site': "same-site",
        'sec-ch-ua-mobile': "?0",
        'sec-ch-ua-platform': "\"Windows\"",
        'Cookie': "locale=en-us"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            print("签到成功")
            return "签到成功"
        else:
            msg = f"签到失败: {data.get('message', '未知错误')}"
            print(msg)
            return msg
    except Exception as e:
        msg = f"签到请求异常: {str(e)}"
        print(msg)
        return msg


if __name__ == "__main__":
    # 优先从环境变量读取
    pzhttp = os.environ.get('pzhttp', '').strip()

    # 如果环境变量为空，尝试从配置文件读取
    if not pzhttp:
        config_file = 'config.txt'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    pzhttp = f.read().strip()
            except Exception as e:
                print(f"读取配置文件失败: {str(e)}")

    if not pzhttp:
        print("未配置账号信息")
        print("请使用以下两种方式之一:")
        print("1. 设置环境变量 pzhttp")
        print("2. 创建 config.txt 文件，格式为: 账号#密码，多账号用换行隔开")
        print("   例如:")
        print("   16663962066#yaohong172016")
        print("   账号2#密码2")
        exit(1)

    accounts = [line.strip() for line in pzhttp.split('\n') if line.strip()]
    print(f"📱 检测到 {len(accounts)} 个账号，开始签到...")

    notify_body = []
    notify_body.append(f"品赞代理签到｜共 {len(accounts)} 账号\n")

    for idx, acc_line in enumerate(accounts, 1):
        try:
            phone, password = acc_line.split('#')
            print(f"\n--- 账号 {idx}: {phone} ---")
            token, login_msg = login(phone, password)
            line = f"【账号{idx} {phone}】\n  {login_msg}\n"
            if token:
                _, wallet_msg = get_wallet_info(token)
                sign_msg = sign_in(token)
                line += f"  {wallet_msg}\n  {sign_msg}\n"
            notify_body.append(line)
        except ValueError:
            err = f"【账号{idx}】格式错误：{acc_line}（应为账号#密码）\n"
            print(err)
            notify_body.append(err)
        except Exception as e:
            err = f"【账号{idx}】处理异常：{str(e)}\n"
            print(err)
            notify_body.append(err)

    notify_body.append("\n🎉 所有账号签到完成")
    full_msg = ''.join(notify_body)

    # 使用你指定的 notify_user 发送
    notify_user("品赞HTTP代理签到", full_msg)

    print("\n🎉 所有账号签到完成")
