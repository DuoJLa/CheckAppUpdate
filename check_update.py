import requests
import json
import os
from datetime import datetime

# iTunes API查询应用信息
ITUNES_API = "https://itunes.apple.com/lookup"
# Bark推送API
BARK_API = "https://api.day.app"
# Telegram Bot API
TELEGRAM_API = "https://api.telegram.org/bot"

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

def get_app_info(app_id):
    """通过iTunes API获取应用信息"""
    try:
        response = requests.get(f"{ITUNES_API}?id={app_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('resultCount', 0) > 0:
                return data['results'][0]
    except Exception as e:
        print(f"获取应用 {app_id} 信息失败: {e}")
    return None

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
            print(f"✅ Bark推送成功: {title}")
            return True
        else:
            print(f"❌ Bark推送失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ Bark推送失败: {e}")
    return False

def send_telegram_notification(bot_token, chat_id, title, content, url=None):
    """发送Telegram Bot推送通知"""
    try:
        # 构建消息文本（支持Markdown格式）
        message = f"*{title}*\n\n{content}"
        if url:
            message += f"\n\n[🔗 在App Store中查看]({url})"
        
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
            print(f"✅ Telegram推送成功: {title}")
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
        
        return send_telegram_notification(bot_token, chat_id, title, content, url)
    
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
    print("-" * 50)
    
    version_cache = load_version_cache()
    updated = False
    
    for app_id in app_ids:
        print(f"🔍 检查应用: {app_id}")
        app_info = get_app_info(app_id)
        
        if not app_info:
            print(f"⚠️  无法获取应用信息")
            continue
        
        app_name = app_info.get('trackName', 'Unknown')
        current_version = app_info.get('version', '0.0.0')
        release_notes = app_info.get('releaseNotes', '无更新说明')
        app_url = app_info.get('trackViewUrl', '')
        
        cached_version = version_cache.get(app_id, {}).get('version', '')
        
        if cached_version != current_version:
            print(f"🎉 检测到更新: {app_name} {cached_version} -> {current_version}")
            
            # 构建推送消息
            title = f"📱 {app_name} 已更新"
            content = f"版本: {current_version}\n\n更新内容:\n{release_notes[:200]}"
            
            # 发送推送
            send_notification(title, content, app_url)
            
            # 更新缓存
            version_cache[app_id] = {
                'version': current_version,
                'app_name': app_name,
                'updated_at': datetime.now().isoformat()
            }
            updated = True
        else:
            print(f"✓ 无更新: {app_name} (v{current_version})")
        
        print("-" * 50)
    
    if updated:
        save_version_cache(version_cache)
        print("💾 版本缓存已更新")
    else:
        print("😴 所有应用均为最新版本")

if __name__ == '__main__':
    check_updates()
