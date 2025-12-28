import requests
import json
import os
from datetime import datetime, timezone

# iTunes API查询应用信息
ITUNES_API = "https://itunes.apple.com/lookup"
# Bark推送API
BARK_API = "https://api.day.app"
# Telegram Bot API
TELEGRAM_API = "https://api.telegram.org/bot"

# 常用App Store地区代码（按使用频率排序）
REGIONS = [
    'cn',  # 中国
    'us',  # 美国
    'hk',  # 香港
    'tw',  # 台湾
    'jp',  # 日本
    'kr',  # 韩国
    'gb',  # 英国
    'sg',  # 新加坡
    'au',  # 澳大利亚
    'de',  # 德国
    'fr',  # 法国
    'ca',  # 加拿大
    'it',  # 意大利
    'es',  # 西班牙
    'ru',  # 俄罗斯
    'br',  # 巴西
    'mx',  # 墨西哥
    'in',  # 印度
    'th',  # 泰国
    'vn',  # 越南
]

# 地区名称映射（中文）
REGION_NAMES = {
    'cn': '中国', 'us': '美国', 'hk': '香港', 'tw': '台湾', 'jp': '日本',
    'kr': '韩国', 'gb': '英国', 'sg': '新加坡', 'au': '澳大利亚',
    'de': '德国', 'fr': '法国', 'ca': '加拿大', 'it': '意大利',
    'es': '西班牙', 'ru': '俄罗斯', 'br': '巴西', 'mx': '墨西哥',
    'in': '印度', 'th': '泰国', 'vn': '越南',
}

def get_push_method():
    """获取推送方式: bark 或 telegram"""
    return os.getenv('PUSH_METHOD', 'bark').lower()

def get_bark_key():
    """从环境变量获取Bark Key"""
    return os.getenv('BARK_KEY', '')

def get_telegram_config():
    """从环境变量获取Telegram配置"""
    return {
        'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
        'chat_id': os.getenv('TELEGRAM_CHAT_ID', '')
    }

def get_app_ids():
    """从环境变量获取App ID列表"""
    ids = os.getenv('APP_IDS', '')
    return [id.strip() for id in ids.split(',') if id.strip()]

def load_version_cache():
    """加载本地版本缓存"""
    try:
        with open('version_cache.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_version_cache(cache):
    """保存版本缓存"""
    with open('version_cache.json', 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_app_info_with_region(app_id):
    """通过iTunes API获取应用信息，自动尝试不同地区"""
    for region in REGIONS:
        try:
            params = {
                'id': app_id,
                'country': region
            }
            response = requests.get(ITUNES_API, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('resultCount', 0) > 0:
                    app_info = data['results'][0]
                    app_info['detected_region'] = region  # 记录找到的地区
                    print(f"✓ 在 {REGION_NAMES.get(region, region)} App Store 找到应用")
                    return app_info
        except Exception as e:
            print(f"查询地区 {region} 时出错: {e}")
            continue
    
    print(f"✗ 在所有地区都未找到应用 ID: {app_id}")
    return None

def format_datetime(iso_datetime):
    """格式化ISO 8601时间为易读格式"""
    try:
        dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
        # 转换为北京时间（UTC+8）
        local_dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return local_dt.strftime('%Y-%m-%d %H:%M')
    except:
        return iso_datetime

def send_bark_notification(bark_key, title, content, url=None):
    """发送Bark推送通知"""
    try:
        data = {
            "title": title,
            "body": content,
            "group": "App Store更新",
            "sound": "bell",
            "isArchive": "1"
        }
        if url:
            data["url"] = url
        
        response = requests.post(f"{BARK_API}/{bark_key}", data=data, timeout=10)
        if response.status_code == 200:
            print(f"✅ Bark推送成功")
            return True
        else:
            print(f"❌ Bark推送失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ Bark推送失败: {e}")
    return False

def send_telegram_notification(bot_token, chat_id, title, content):
    """发送Telegram Bot推送通知"""
    try:
        # 构建消息文本（使用Markdown格式）
        message = f"*{title}*\n\n{content}"
        
        # 发送消息
        api_url = f"{TELEGRAM_API}{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        
        response = requests.post(api_url, json=payload, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            print(f"✅ Telegram推送成功")
            return True
        else:
            print(f"❌ Telegram推送失败: {result.get('description', '未知错误')}")
    except Exception as e:
        print(f"❌ Telegram推送失败: {e}")
    return False

def send_notification(title, content, url=None):
    """根据配置选择推送方式"""
    push_method = get_push_method()
    
    if push_method == 'telegram':
        telegram_config = get_telegram_config()
        bot_token = telegram_config['bot_token']
        chat_id = telegram_config['chat_id']
        
        if not bot_token or not chat_id:
            print("❌ 错误: 未设置TELEGRAM_BOT_TOKEN或TELEGRAM_CHAT_ID")
            return False
        
        return send_telegram_notification(bot_token, chat_id, title, content)
    
    elif push_method == 'bark':
        bark_key = get_bark_key()
        
        if not bark_key:
            print("❌ 错误: 未设置BARK_KEY")
            return False
        
        return send_bark_notification(bark_key, title, content, url)
    
    else:
        print(f"❌ 错误: 不支持的推送方式 '{push_method}'，请使用 'bark' 或 'telegram'")
        return False

def check_updates():
    """检查应用更新"""
    app_ids = get_app_ids()
    push_method = get_push_method()
    
    if not app_ids:
        print("❌ 错误: 未设置APP_IDS")
        return
    
    print(f"📢 推送方式: {push_method.upper()}")
    print(f"📱 监控应用数量: {len(app_ids)}")
    print("=" * 60)
    
    version_cache = load_version_cache()
    updated_apps = []  # 存储所有有更新的应用信息
    
    for app_id in app_ids:
        print(f"\n🔍 检查应用: {app_id}")
        app_info = get_app_info_with_region(app_id)
        
        if not app_info:
            print(f"⚠️  无法获取应用信息")
            continue
        
        app_name = app_info.get('trackName', 'Unknown')
        current_version = app_info.get('version', '0.0.0')
        release_notes = app_info.get('releaseNotes', '无更新说明')
        app_url = app_info.get('trackViewUrl', '')
        release_date = app_info.get('currentVersionReleaseDate', '')
        region = app_info.get('detected_region', 'us')
        region_name = REGION_NAMES.get(region, region.upper())
        
        # 格式化更新时间
        formatted_date = format_datetime(release_date) if release_date else '未知'
        
        cached_version = version_cache.get(app_id, {}).get('version', '')
        
        if cached_version != current_version:
            print(f"🎉 检测到更新: {app_name}")
            print(f"   版本: {cached_version} -> {current_version}")
            print(f"   地区: {region_name}")
            print(f"   更新时间: {formatted_date}")
            
            # 收集更新信息
            update_info = {
                'app_name': app_name,
                'old_version': cached_version if cached_version else '首次检测',
                'new_version': current_version,
                'release_notes': release_notes,
                'release_date': formatted_date,
                'app_url': app_url,
                'region': region_name
            }
            updated_apps.append(update_info)
            
            # 更新缓存
            version_cache[app_id] = {
                'version': current_version,
                'app_name': app_name,
                'region': region,
                'updated_at': datetime.now().isoformat()
            }
        else:
            print(f"✓ 无更新: {app_name} (v{current_version}) - {region_name}")
    
    print("\n" + "=" * 60)
    
    # 如果有更新，发送整合的推送消息
    if updated_apps:
        print(f"\n📦 共发现 {len(updated_apps)} 个应用更新")
        
        # 构建整合的推送消息
        if len(updated_apps) == 1:
            # 单个应用更新
            app = updated_apps[0]
            title = f"📱 {app['app_name']} 已更新"
            content = (
                f"版本: {app['new_version']}\n"
                f"地区: {app['region']}\n"
                f"更新时间: {app['release_date']}\n\n"
                f"更新内容:\n{app['release_notes'][:300]}"
            )
            
            if push_method == 'bark':
                # Bark支持URL参数
                send_notification(title, content, app['app_url'])
            else:
                # Telegram在消息中添加链接
                content += f"\n\n🔗 [{app['app_name']}]({app['app_url']})"
                send_notification(title, content)
        else:
            # 多个应用更新
            title = f"📱 App Store 更新通知 ({len(updated_apps)}个)"
            
            # 构建消息内容
            content_parts = []
            app_urls = []
            
            for i, app in enumerate(updated_apps, 1):
                app_content = (
                    f"{i}. *{app['app_name']}* v{app['new_version']}\n"
                    f"   地区: {app['region']} | 更新: {app['release_date']}\n"
                    f"   {app['release_notes'][:100]}{'...' if len(app['release_notes']) > 100 else ''}\n"
                )
                content_parts.append(app_content)
                app_urls.append(app['app_url'])
            
            content = "\n".join(content_parts)
            
            if push_method == 'bark':
                # Bark只能跳转一个URL，使用第一个应用的URL
                send_notification(title, content, app_urls[0] if app_urls else None)
            else:
                # Telegram添加所有应用链接
                links = "\n".join([f"🔗 [{app['app_name']}]({app['app_url']})" 
                                  for app in updated_apps])
                content += f"\n\n{links}"
                send_notification(title, content)
        
        # 保存更新后的缓存
        save_version_cache(version_cache)
        print("💾 版本缓存已更新")
    else:
        print("😴 所有应用均为最新版本")

if __name__ == '__main__':
    check_updates()
