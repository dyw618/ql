#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 青龙变量只需要：
#   xcplus 多号：换行 或 @ 分割
#   账号格式：备注#x-vayne#x-teemo#x-sivir
#   也支持：备注#x-vayne#x-teemo#x-sivir#平台订单号
#
# 其他配置直接改下面的变量。
# 必填订单号：
#   方式1：账号后追加 #平台订单号
#   方式2：设置 PLATFORM_ORDER_IDS，多个订单号用换行或 @ 分割，顺序对应 xcbm

import hashlib
import json
import os
import time
from urllib.parse import urlparse

import requests
import uuid
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RPC_URL = "https://gw.xiaocantech.com/rpc"
GW_RPC_URL = "https://gw.xiaocantech.com/rpc"

# 活动关键词；ACTIVITY_ID 为空时按关键词查询并取第一个活动。
KEYWORD = "茶百道"
# 平台订单号；多账号用换行或 @ 分割。也可以写在 xcbm 的后面。
PLATFORM_ORDER_IDS = ""
# True 表示只打印活动和卡券列表，不报名、不提交订单号。
LIST_ACTIVITIES = False

# 唯一从青龙环境变量读取的变量名。
COOKIE_ENV = "xcbm"

# 接口请求超时秒数。
HTTP_TIMEOUT = 10

# 多账号顺序执行时，每个账号之间的间隔秒数。
REQUEST_INTERVAL = 1

# 指定活动 ID；留空则用 KEYWORD 自动查询。
ACTIVITY_ID = ""

# 小程序 app_id
APP_ID = 20

# 城市编码
CITY_CODE = 430105

# 接口版本号
VERSION = "3.18.4.38"

# 大牌券类型
CARD_TYPE = 13

# 每页读取卡券数量。
CARD_PAGE_SIZE = 10

# 最多读取多少页卡包，用于寻找最快过期的大牌券。
MAX_CARD_PAGES = 5

# 定位纬度，用于查活动和报名。
LAT = 28.255911

# 定位经度，用于查活动和报名。
LNG = 112.986259


def ts_print(*args, **kwargs):
    print(*args, **kwargs)


def md5(text):
    return hashlib.md5(text.encode()).hexdigest()


def read_xcplus():
    return os.getenv(COOKIE_ENV, "").strip()


def split_multi(value):
    return [item.strip() for item in value.replace("\n", "@").split("@") if item.strip()]


def require_ok(method_name, result):
    status = result.get("status", {}) if isinstance(result, dict) else {}
    if status.get("code") != 0:
        raise RuntimeError(f"{method_name} 失败: {status.get('msg') or result}")
    return result


def card_expire_time(card_item):
    value = card_item.get("expire_time")
    return value if isinstance(value, int) else 10 ** 18


def is_big_brand_coupon(card_item, card_type):
    card = card_item.get("card") or {}
    name = str(card.get("name") or "")
    return "大牌" in name or str(card.get("card_type") or "") == str(card_type)


def build_retry_adapter():
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["POST"]),
    )
    return HTTPAdapter(max_retries=retry)


class Account:
    def __init__(self, raw):
        parts = raw.strip().split("#")
        if len(parts) not in (4, 5):
            raise ValueError("账号格式应为: 备注#x-vayne#x-teemo#x-sivir[#平台订单号]")
        self.note = parts[0]
        self.user_id = parts[1]
        self.silk_id = parts[2]
        self.token = parts[3]
        self.platform_order_id = parts[4].strip() if len(parts) == 5 else ""
        if not self.user_id.isdigit() or not self.silk_id.isdigit() or not self.token:
            raise ValueError("账号内容无效")


class Config:
    def __init__(self):
        self.keyword = str(KEYWORD).strip()
        self.activity_id = str(ACTIVITY_ID).strip()
        self.card_type = int(CARD_TYPE)
        self.card_page_size = int(CARD_PAGE_SIZE)
        self.max_card_pages = int(MAX_CARD_PAGES)
        self.lat = float(LAT)
        self.lng = float(LNG)
        self.city_code = int(CITY_CODE)
        self.app_id = int(APP_ID)
        self.version = str(VERSION)
        self.list_only = bool(LIST_ACTIVITIES)
        self.platform_order_ids = split_multi(str(PLATFORM_ORDER_IDS))


class XiaocanOrderBot:
    def __init__(self, account, config):
        self.account = account
        self.config = config
        self.session_id = str(uuid.uuid4())
        self.session = requests.Session()
        self.session.mount("https://", build_retry_adapter())
        self.headers = self.build_base_headers()

    def log(self, message):
        ts_print(f"[{self.account.note or self.account.silk_id}] {message}")

    def build_base_headers(self):
        return {
            "appid": str(self.config.app_id),
            "x-vayne": self.account.user_id,
            "x-annie": "XC",
            "xweb_xhr": "1",
            "x-teemo": self.account.silk_id,
            "x-ashe": "",
            "x-model": "microsoft microsoft",
            "content-type": "application/json",
            "x-session-id": self.session_id,
            "x-nami": "",
            "x-platform": "iOS",
            "x-version": self.config.version,
            "servername": "",
            "x-sivir": self.account.token,
            "methodname": "",
            "x-city": str(self.config.city_code),
            "x-garen": "",
            "version": self.config.version,
            "accept": "*/*",
            "referer": "https://servicewechat.com/wx52ae177248081591/770/page-frame.html",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) xcapp;3.18.4.38;iOS",
        }

    def refresh_auth_headers(self, server_name, method_name, url):
        request_id = uuid.uuid4().hex
        tail_len = max(0, 16 - len(self.account.silk_id) - 4)
        x_nami = request_id[:4] + self.account.silk_id + request_id[4: 4 + tail_len]
        x_garen = str(int(time.time() * 1000))
        service_method = f"{server_name}.{method_name}".lower()
        x_ashe = md5(md5(service_method) + x_garen + x_nami)
        self.headers.update(
            {
                "host": urlparse(url).netloc,
                "servername": server_name,
                "methodname": method_name,
                "x-nami": x_nami,
                "x-garen": x_garen,
                "x-ashe": x_ashe,
            }
        )

    def rpc(self, server_name, method_name, data, url=RPC_URL):
        self.refresh_auth_headers(server_name, method_name, url)
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        response = self.session.post(
            url,
            headers=self.headers,
            data=payload.encode(),
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise RuntimeError(f"{method_name} 返回格式异常: {result}")
        return result

    def silk_id_int(self):
        return int(self.account.silk_id)

    def base_payload(self, **extra):
        payload = {"silk_id": self.silk_id_int()}
        payload.update(extra)
        return payload

    def list_activities(self):
        data = self.base_payload(
            city_code=self.config.city_code // 100,
            lat=self.config.lat,
            lng=self.config.lng,
            page=1,
            page_size=20,
            keywords=self.config.keyword,
            f_id=0,
            activity_ids=[],
            brands=[],
            categories=[],
            is_filter_top_brand=False,
        )
        return require_ok(
            "TopBrandService.CouponActivities",
            self.rpc("TopBrand", "TopBrandService.CouponActivities", data, url=GW_RPC_URL),
        )

    def pick_activity_id(self):
        if self.config.activity_id:
            return int(self.config.activity_id)
        result = self.list_activities()
        activities = result.get("coupon_activities") or []
        if not activities:
            raise RuntimeError("没有查到可报名活动，请设置 KEYWORD 或 ACTIVITY_ID")
        picked = activities[0]
        self.log(
            f"自动选择活动: activity_id={picked.get('activity_id')}, "
            f"brand={picked.get('brand_name')}, benefit={picked.get('benefit')}"
        )
        return int(picked["activity_id"])

    def activity_detail(self, activity_id):
        data = self.base_payload(
            activity_id=int(activity_id),
            lng=self.config.lng,
            lat=self.config.lat,
            app_id=self.config.app_id,
        )
        return require_ok(
            "TopBrandService.ActivityDetail",
            self.rpc("TopBrand", "TopBrandService.ActivityDetail", data),
        )

    def user_card_list(self, offset=0, number=10):
        data = self.base_payload(
            status=0,
            offset=int(offset),
            number=int(number),
            app_id=self.config.app_id,
        )
        return require_ok(
            "SilkwormCardService.GetUserCardList",
            self.rpc("SilkwormCard", "SilkwormCardService.GetUserCardList", data),
        )

    def fetch_user_cards(self):
        cards = []
        offset = 0
        for _ in range(self.config.max_card_pages):
            page = self.user_card_list(offset, self.config.card_page_size).get("list") or []
            cards.extend(page)
            if len(page) < self.config.card_page_size:
                break
            offset += self.config.card_page_size
        return cards

    def pick_brand_coupon_id(self):
        cards = self.fetch_user_cards()
        candidates = [item for item in cards if is_big_brand_coupon(item, self.config.card_type)]
        if not candidates:
            raise RuntimeError("没有可用大牌券")
        picked = sorted(
            candidates,
            key=lambda item: (card_expire_time(item), int(item.get("id") or 0)),
        )[0]
        card = picked.get("card") or {}
        self.log(
            f"自动选择最快过期大牌券: brand_coupon_id={picked.get('id')}, "
            f"name={card.get('name')}, expire_time={picked.get('expire_time')}"
        )
        return int(picked["id"])

    def activity_sign(self, activity_id, brand_coupon_id):
        data = self.base_payload(
            lat=self.config.lat,
            lng=self.config.lng,
            activity_id=int(activity_id),
            brand_coupon_id=int(brand_coupon_id),
            card_type=self.config.card_type,
            app_id=self.config.app_id,
        )
        return require_ok(
            "TopBrandService.ActivitySign",
            self.rpc("TopBrand", "TopBrandService.ActivitySign", data),
        )

    def get_order(self, promotion_order_id):
        data = self.base_payload(
            promotion_order_id=int(promotion_order_id),
            app_id=self.config.app_id,
        )
        return require_ok(
            "SilkwormService.GetClientPromotionOrder",
            self.rpc("Silkworm", "SilkwormService.GetClientPromotionOrder", data),
        )

    def upload_order_id(self, promotion_order_id, platform_order_id):
        data = self.base_payload(
            promotion_order_id=int(promotion_order_id),
            platform_order_id=str(platform_order_id),
            app_id=self.config.app_id,
        )
        return require_ok(
            "TopBrandService.UploadOrder",
            self.rpc("TopBrand", "TopBrandService.UploadOrder", data),
        )

    def print_list_only(self):
        activities = self.list_activities().get("coupon_activities") or []
        self.log(f"活动数量: {len(activities)}")
        for item in activities:
            self.log(
                f"activity_id={item.get('activity_id')} "
                f"brand={item.get('brand_name')} "
                f"benefit={item.get('benefit')} "
                f"min={item.get('min')} "
                f"left={item.get('left', '')}"
            )

        cards = sorted(self.fetch_user_cards(), key=card_expire_time)
        self.log(f"卡券数量: {len(cards)}")
        for item in cards:
            card = item.get("card") or {}
            marker = " [大牌候选]" if is_big_brand_coupon(item, self.config.card_type) else ""
            self.log(
                f"brand_coupon_id={item.get('id')} "
                f"card_type={card.get('card_type')} "
                f"name={card.get('name')} "
                f"expire_time={item.get('expire_time')}"
                f"{marker}"
            )

    def submit_order(self, platform_order_id):
        activity_id = self.pick_activity_id()
        brand_coupon_id = self.pick_brand_coupon_id()
        self.activity_detail(activity_id)
        sign_result = self.activity_sign(activity_id, brand_coupon_id)
        promotion_order_id = sign_result.get("promotion_order_id")
        if not promotion_order_id:
            raise RuntimeError(f"报名成功但未返回 promotion_order_id: {sign_result}")
        self.log(f"报名成功: promotion_order_id={promotion_order_id}")

        before = self.get_order(promotion_order_id).get("promotion_order") or {}
        self.log(
            f"提交前状态: order_status={before.get('order_status')} "
            f"union_order_status={before.get('union_order_status')} "
            f"platform_order_id={before.get('platform_order_id')}"
        )

        if str(before.get("platform_order_id") or "") == str(platform_order_id):
            self.log("平台订单号已存在且一致，跳过重复提交")
        else:
            result = self.upload_order_id(promotion_order_id, platform_order_id)
            self.log(f"平台订单号提交完成: po_status={result.get('po_status')}")

        after = self.get_order(promotion_order_id).get("promotion_order") or {}
        self.log(
            f"提交后状态: order_status={after.get('order_status')} "
            f"union_order_status={after.get('union_order_status')} "
            f"platform_order_id={after.get('platform_order_id')}"
        )


def resolve_aligned_value(values, index, total, name):
    if not values:
        return ""
    if len(values) == total:
        return values[index - 1]
    if total == 1 and len(values) == 1:
        return values[0]
    raise ValueError(f"{name} 数量应与账号数一致")


def run_one(raw_account, index, total, config):
    account = Account(raw_account)
    platform_order_id = account.platform_order_id or resolve_aligned_value(
        config.platform_order_ids,
        index,
        total,
        "PLATFORM_ORDER_IDS",
    )

    bot = XiaocanOrderBot(account, config)
    if config.list_only:
        bot.print_list_only()
        return True

    if not platform_order_id:
        raise ValueError("缺少平台订单号：账号后追加 #平台订单号，或设置 PLATFORM_ORDER_IDS")

    bot.submit_order(platform_order_id)
    return True


def main():
    cookie_text = read_xcplus()
    if not cookie_text:
        ts_print(f"请设置青龙变量 {COOKIE_ENV}")
        return

    accounts = split_multi(cookie_text)
    config = Config()
    total = len(accounts)

    ts_print("=" * 50)
    ts_print("小蚕霸王餐 - 报名并提交平台订单号")
    ts_print(f"账号数: {total} | 顺序执行")
    ts_print(f"关键词: {config.keyword or '-'} | activity_id: {config.activity_id or '自动'}")
    ts_print("大牌券: 自动选择最快过期")
    ts_print("=" * 50)

    start = time.time()
    results = []
    for idx, raw in enumerate(accounts, start=1):
        try:
            run_one(raw, idx, total, config)
            results.append((idx, True, ""))
        except Exception as exc:
            ts_print(f"[账号{idx}] 执行失败: {exc}")
            results.append((idx, False, str(exc)))
        if idx < total:
            time.sleep(REQUEST_INTERVAL)

    ok_count = sum(1 for _, ok, _ in results if ok)
    fail_count = total - ok_count
    ts_print("=" * 50)
    ts_print(f"执行完成 | 成功: {ok_count} | 失败: {fail_count} | 耗时: {time.time() - start:.1f}s")
    ts_print("=" * 50)


if __name__ == "__main__":
    main()
