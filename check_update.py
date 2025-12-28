import requests
import json
import os
from datetime import datetime, timezone, timedelta

ITUNES_API = "https://itunes.apple.com/lookup"
BARK_API = "https://api.day.app"
TELEGRAM_API = "https://api.telegram.org/bot"

CACHE_FILE = "version_cache.json"

REGIONS = [
    "cn", "us", "hk", "tw", "jp", "kr", "gb", "sg", "au",
    "de", "fr", "ca", "it", "es", "ru", "br", "mx", "in", "th", "vn"
]

REGION_NAMES = {
    "cn": "中国", "us": "美国", "hk": "香港", "tw": "台湾", "jp": "日本",
    "kr": "韩国", "gb": "英国", "sg": "新加坡", "au": "澳大利亚",
    "de": "德国", "fr": "法国", "ca": "加拿大", "it": "意大利",
    "es": "西班牙", "ru": "俄罗斯", "br": "巴西", "mx": "墨西哥",
    "in": "印度", "th": "泰国", "vn": "越南",
}

TEST_APP_IDS = ["414478124"]  # 微信

def get_push_method():
    return os.getenv("PUSH_METHOD", "bark").lower()

def get_bark_key():
    return os.getenv("BARK_KEY", "")

def get_telegram_config():
    return {
        "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "chat_id": os.getenv("TELEGRAM_CHAT_ID", "")
    }

def get_app_ids():
    env_ids = os.getenv("APP_IDS", "")
    if env_ids:
        ids = [i.strip() for i in env_ids.split(",") if i.strip()]
        print(f"📋 从环境变量获取 App ID: {ids}")
        return ids
    print("⚠️ 未设置 APP_IDS，使用测试 ID: 414478124 (微信)")
    return TEST_APP_IDS

def load_version_cache():
    try:
        if not os.path.exists(CACHE_FILE):
            print("📂 缓存文件不存在 -> 首次运行")
            return {}
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                print(f"📂 缓存库加载成功，共 {len(data)} 个应用")
                return data
            print("⚠️ 缓存格式错误，重置为空")
            return {}
    except Exception as e:
        print(f"❌ 加载缓存异常: {e}")
        return {}

def save_version_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"💾 缓存已保存 ({len(cache)} 条记录)")
    except Exception as e:
        print(f"❌ 保存缓存失败: {e}")

def get_app_info_with_region(app_id: str):
    print(f"   尝试查询地区: ", end="")
    for i, region in enumerate(REGIONS[:6]):  # 前6个常用地区
        try:
            if i > 0: print(".", end="", flush=True)
            resp = requests.get(ITUNES_API, params={"id": app_id, "country": region}, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("resultCount", 0) > 0:
                    app = data["results"][0]
                    app["detected_region"] = region
                    print(f"\n   ✓ [{region}] {app.get('trackName', 'Unknown')} v{app.get('version', '?')}")
                    return app
        except:
            continue
    print(" ✗ 全部失败")
    return None

def format_datetime(iso_datetime: str) -> str:
    if not iso_datetime: return "未知"
    try:
        dt = datetime.fromisoformat(iso_datetime.replace("Z", "+00:00"))
        utc_plus_8 = dt + timedelta(hours=8)
        return utc_plus_8.strftime("%Y-%m-%d %H:%M")
    except:
        return iso_datetime[:16]

def send_bark_notification(bark_key, title, content, url=None, icon_url=None):
    try:
        data = {"title": title, "body": content, "group": "App Store更新", "sound": "bell", "isArchive": "1"}
        if url: data["url"] = url
        if icon_url: data["icon"] = icon_url
        resp = requests.post(f"{BARK_API}/{bark_key}", data=data, timeout=10)
        print(f"📱 Bark: {'✅成功' if resp.status_code == 200 else f'❌{resp.status_code}'}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Bark异常: {e}")
        return False

def send_telegram_notification(bot_token, chat_id, title, content):
    try:
        message = f"*{title}*\n\n{content}"
        url = f"{TELEGRAM_API}{bot_token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        print(f"📱 Telegram: {'✅成功' if resp.json().get('ok') else '❌失败'}")
        return resp.json().get('ok')
    except:
        print("❌ Telegram异常")
        return False

def send_notification(title, content, url=None, icon_url=None):
    method = get_push_method()
    if method == "bark":
        key = get_bark_key()
        return bool(key) and send_bark_notification(key, title, content, url, icon_url)
    elif method == "telegram":
        cfg = get_telegram_config()
        return bool(cfg["bot_token"] and cfg["chat_id"]) and send_telegram_notification(cfg["bot_token"], cfg["chat_id"], title, content)
    return False

def check_updates():
    print("🚀 App Store 更新监控启动")
    app_ids = get_app_ids()
    print(f"📢 推送方式: {get_push_method()}")
    print(f"📱 监控: {app_ids}")
    print("=" * 50)

    cache = load_version_cache()
    is_first_run = len(cache) == 0
    print(f"🔄 {'首次运行' if is_first_run else '后续运行'} (缓存: {len(cache)} 条)")

    all_current_apps = []
    updated_apps = []

    for app_id in app_ids:
        print(f"\n🔍 检查 {app_id}")
        info = get_app_info_with_region(app_id)
        if not info: continue

        name = info.get("trackName", "Unknown")
        version = info.get("version", "0.0")
        region_code = info.get("detected_region", "us")
        region_name = REGION_NAMES.get(region_code, region_code.upper())
        icon = info.get("artworkUrl100", "")
        old_version = cache.get(app_id, {}).get("version", "")

        if is_first_run or old_version != version:
            app_data = {"id": app_id, "name": name, "version": version, "region": region_name, "icon": icon, "old_version": old_version}
            if is_first_run:
                print(f"   📝 初始化: {name} v{version}")
                all_current_apps.append(app_data)
            else:
                print(f"   🎉 更新: {name} {old_version or '无'} → v{version}")
                updated_apps.append(app_data)
            
            cache[app_id] = {"version": version, "app_name": name, "region": region_code, "icon": icon, "updated_at": datetime.now().isoformat()}
        else:
            print(f"   ✅ 最新: {name} v{version}")

    print("\n" + "=" * 50)
    
    if is_first_run and all_current_apps:
        title = f"📱 监控初始化完成 ({len(all_current_apps)} 应用)"
        content = "\n".join([f"• {app['name']} v{app['version']} ({app['region']})" for app in all_current_apps])
        first_app = all_current_apps[0]
        send_notification(title, content, first_app["icon"])
        save_version_cache(cache)
        print("✅ 首次运行完成！")
    elif updated_apps:
        title = f"📱 更新通知 ({len(updated_apps)} 个)"
        content = "\n".join([f"• {app['name']}: v{app['old_version']} → v{app['version']}" for app in updated_apps])
        first_app = updated_apps[0]
        send_notification(title, content, first_app["icon"])
        save_version_cache(cache)
        print("✅ 更新通知发送完成！")
    else:
        print("😊 一切正常")

if __name__ == "__main__":
    check_updates()
