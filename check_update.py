import requests
import json
import os
from datetime import datetime, timedelta

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
    """修复：正确处理环境变量逻辑"""
    env_ids = os.getenv("APP_IDS", "")
    if env_ids:
        ids = [i.strip() for i in env_ids.split(",") if i.strip()]
        print(f"📋 从环境变量获取 App ID: {ids}")
        return ids
    print("⚠️ 未设置 APP_IDS，使用测试 ID: 414478124 (微信)")
    return TEST_APP_IDS

def load_version_cache():
    """加载缓存库，增加详细日志"""
    try:
        if not os.path.exists(CACHE_FILE):
            print("📂 缓存文件不存在 -> 首次运行")
            return {}
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                print(f"📂 缓存库加载成功，共 {len(data)} 个应用:")
                for app_id, info in list(data.items())[:3]:
                    print(f"   {app_id}: v{info.get('version', '?')} ({info.get('app_name', '?')})")
                if len(data) > 3:
                    print(f"   ... 还有 {len(data)-3} 个应用")
                return data
                print("⚠️ 缓存格式错误，重置为空")
                return {}
    except Exception as e:
        print(f"❌ 加载缓存异常: {e}")
        return {}

def save_version_cache(cache):
    """保存缓存，强制写入"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"💾 缓存已保存到 {CACHE_FILE} ({len(cache)} 条记录)")
        print("📋 当前缓存内容:")
        for app_id, info in list(cache.items())[:3]:
            print(f"   {app_id}: v{info['version']} ({info['app_name']})")
        if len(cache) > 3:
            print(f"   ... 共 {len(cache)} 条")
    except Exception as e:
        print(f"❌ 保存缓存失败: {e}")

def get_app_info_with_region(app_id: str):
    """查询应用信息，增加详细调试"""
    print(f"   尝试查询地区: ", end="")
    for i, region in enumerate(REGIONS[:6]):  # 前6个常用地区
        try:
            if i > 0:
                print(".", end="", flush=True)
            resp = requests.get(
                ITUNES_API,
                params={"id": app_id, "country": region},
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                print(f"\n   [{region}] resultCount={data.get('resultCount', 0)}")
                if data.get("resultCount", 0) > 0:
                    app = data["results"][0]
                    app["detected_region"] = region
                    print(f"   ✓ 找到: {app.get('trackName', 'Unknown')} v{app.get('version', '?')}")
                    return app
        except Exception as e:
            print(f"\n   [{region}] 异常: {str(e)[:30]}...", end="")
            continue
    print(" ✗ 全部失败")
    return None

def format_datetime(iso_datetime: str) -> str:
    """修复：使用 timedelta 替代 zoneinfo（兼容Python 3.10）"""
    if not iso_datetime:
        return "未知"
    try:
        dt = datetime.fromisoformat(iso_datetime.replace("Z", "+00:00"))
        utc_plus_8 = dt + timedelta(hours=8)
        return utc_plus_8.strftime("%Y-%m-%d %H:%M")
    except:
        return iso_datetime[:16]

def send_bark_notification(bark_key, title, content, url=None, icon_url=None):
    try:
        data = {
            "title": title,
            "body": content,
            "group": "App Store更新",
            "sound": "bell",
            "isArchive": "1",
        }
        if url: data["url"] = url
        if icon_url: data["icon"] = icon_url
        resp = requests.post(f"{BARK_API}/{bark_key}", data=data, timeout=10)
        success = resp.status_code == 200
        print(f"📱 Bark推送: {'✅成功' if success else f'❌失败({resp.status_code})'}")
        return success
    except Exception as e:
        print(f"❌ Bark推送异常: {e}")
        return False

def send_telegram_notification(bot_token, chat_id, title, content):
    try:
        message = f"*{title}*\n\n{content}"
        url = f"{TELEGRAM_API}{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        success = data.get('ok')
        print(f"📱 Telegram推送: {'✅成功' if success else '❌失败'}")
        return success
    except Exception as e:
        print(f"❌ Telegram推送异常: {e}")
        return False

def send_notification(title, content, url=None, icon_url=None):
    """修复：正确传递参数"""
    method = get_push_method()
    if method == "bark":
        key = get_bark_key()
        if not key:
            print("⚠️ 跳过推送: 未配置 BARK_KEY")
            return False
        return send_bark_notification(key, title, content, url, icon_url)
    elif method == "telegram":
        cfg = get_telegram_config()
        if not cfg["bot_token"] or not cfg["chat_id"]:
            print("⚠️ 跳过推送: Telegram配置不全")
            return False
        return send_telegram_notification(cfg["bot_token"], cfg["chat_id"], title, content)
    print(f"⚠️ 未知推送方式: {method}")
    return False

def build_app_detail(app_data, show_old_version=False):
    """新增：构建详细的应用推送内容"""
    old_ver = f"（{app_data['old_version']}→" if show_old_version and app_data.get('old_version') else ""
    notes = app_data.get('notes', '暂无更新说明')
    if len(notes) > 150:
        notes = notes[:147] + "..."
    
    return f"""📱 {app_data['name']}{old_ver}{app_data['version']} 📱
地区: {app_data['region']} | 更新时间: {app_data['release']}
━━━━━━━━━━━━━━━
{notes}"""

def check_updates():
    print("🚀 App Store 更新监控启动")
    
    app_ids = get_app_ids()
    if not app_ids:
        print("❌ 错误: 没有有效的 App ID")
        return

    print(f"📢 推送方式: {get_push_method()}")
    print(f"📱 要监控 {len(app_ids)} 个应用: {app_ids}")
    print("=" * 60)

    cache = load_version_cache()
    is_first_run = len(cache) == 0
    print(f"🔄 {'首次运行' if is_first_run else '后续运行'} (缓存: {len(cache)} 条)")

    all_current_apps = []
    updated_apps = []

    for app_id in app_ids:
        print(f"\n🔍 [第{app_ids.index(app_id)+1}/{len(app_ids)}] 检查 {app_id}")
        info = get_app_info_with_region(app_id)
        
        if not info:
            print(f"   ⚠️ 跳过: 无法获取应用信息")
            continue

        name = info.get("trackName", "Unknown App")
        version = info.get("version", "0.0")
        notes = info.get("releaseNotes", "暂无更新说明")
        url = info.get("trackViewUrl", "")
        release_iso = info.get("currentVersionReleaseDate", "")
        region_code = info.get("detected_region", "us")
        region_name = REGION_NAMES.get(region_code, region_code.upper())
        icon = info.get("artworkUrl100", "")
        
        release_time = format_datetime(release_iso)
        old_version = cache.get(app_id, {}).get("version", "")

        app_data = {
            "id": app_id,
            "name": name,
            "version": version,
            "region": region_name,
            "icon": icon,
            "old_version": old_version,
            "notes": notes,
            "release": release_time,
            "url": url
        }

        if is_first_run or old_version != version:
            if is_first_run:
                print(f"   📝 初始化: {name} v{version}")
                all_current_apps.append(app_data)
            else:
                print(f"   🎉 更新: {name} {old_version or '无记录'} → v{version}")
                updated_apps.append(app_data)
            
            # 更新缓存
            cache[app_id] = {
                "version": version,
                "app_name": name,
                "region": region_code,
                "icon": icon,
                "updated_at": datetime.now().isoformat(),
            }
        else:
            print(f"   ✅ 最新: {name} v{version}")

    print("\n" + "=" * 60)

    # === 增强推送逻辑 ===
    if is_first_run and all_current_apps:
        title = f"📱 监控初始化完成 ({len(all_current_apps)} 应用)"
        details = "\n\n".join([build_app_detail(app) for app in all_current_apps])
        content = f"✅ 已成功添加以下应用到监控列表：\n\n{details}"
        
        first_app = all_current_apps[0]
        send_notification(title, content, first_app["url"], first_app["icon"])
        save_version_cache(cache)
        print("✅ 首次运行完成，缓存已初始化！")
        
    elif updated_apps:
        if len(updated_apps) == 1:
            # 单个应用详细展示
            app = updated_apps[0]
            title = f"🔥 {app['name']} 有新版本啦！"
            content = build_app_detail(app, show_old_version=True)
            send_notification(title, content, app["url"], app["icon"])
        else:
            # 多个应用列表展示
            title = f"📱 App Store 更新 ({len(updated_apps)} 个)"
            details = "\n\n".join([build_app_detail(app, show_old_version=True) for app in updated_apps])
            content = f"发现以下应用有更新：\n\n{details}"
            
            first_app = updated_apps[0]
            send_notification(title, content, first_app["url"], first_app["icon"])
        
        save_version_cache(cache)
        print("✅ 更新通知已发送，缓存已更新！")
    else:
        print("😊 一切正常，无需通知")

if __name__ == "__main__":
    check_updates()
