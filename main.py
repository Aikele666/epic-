import requests
import os
from datetime import datetime
import html

# 1. 获取 GitHub Secrets
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
CHAT_ID = os.environ.get("TG_CHAT_ID")

def get_chinese_title(slug):
    """
    【新功能】拿着游戏的 Slug 去 Epic 中文详情页接口单独查名字
    这个接口比大列表接口准得多。
    """
    if not slug:
        return None
    
    # Epic 的内容详情接口，支持精准的语言设置
    url = f"https://store-content.ak.epicgames.com/api/zh-CN/content/products/{slug}"
    try:
        # 伪装成浏览器，防止被拦截
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            # 不同的游戏数据结构可能略有不同，尝试获取 productTitle 或 title
            cn_name = data.get('productTitle') or data.get('title')
            return cn_name
    except Exception as e:
        print(f"查询中文名失败 ({slug}): {e}")
    
    return None

def get_epic_free_games():
    # 获取基础列表 (英文为主，用来拿图片和基础信息)
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US"
    try:
        res = requests.get(url).json()
        games = res['data']['Catalog']['searchStore']['elements']
        
        free_games = []
        for game in games:
            # 1. 基础过滤
            promotions = game.get('promotions')
            if not promotions: continue
            if not promotions.get('promotionalOffers'): continue
            
            # 2. 检查价格是否为 0
            offers = promotions['promotionalOffers']
            if not offers: continue

            is_free = False
            end_date_str = "未知"

            for offer_group in offers:
                for offer in offer_group['promotionalOffers']:
                    if offer['discountSetting']['discountPercentage'] == 0:
                        is_free = True
                        raw_date = offer.get('endDate')
                        if raw_date:
                            try:
                                dt = datetime.strptime(raw_date.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                end_date_str = dt.strftime("%Y-%m-%d %H:%M") + " (UTC)"
                            except:
                                end_date_str = raw_date
                        break
            
            if is_free:
                title_en = game.get('title')
                description = game.get('description', '暂无描述')
                slug = game.get('productSlug') or game.get('urlSlug')
                link = f"https://store.epicgames.com/p/{slug}" if slug else "https://store.epicgames.com/free-games"
                
                # 图片获取
                image_url = ""
                for img in game.get('keyImages', []):
                    if img.get('type') == 'Thumbnail':
                        image_url = img.get('url')
                        break
                    elif img.get('type') == 'OfferImageWide':
                        image_url = img.get('url')

                # 【关键修改】单独去查一次中文名
                print(f"正在查询中文名: {title_en} ({slug})...")
                title_cn = get_chinese_title(slug)
                
                # 只有当中文名存在，且和英文名真的不一样时，才显示双语
                # (注意：有些游戏 Epic 官方在国区也只填了英文名，那种情况我们就没办法了)
                display_title = title_en
                if title_cn and title_cn.strip() != title_en.strip():
                    display_title = f"{title_en} <br/>({title_cn})"

                free_games.append({
                    "title": display_title,
                    "description": description,
                    "link": link,
                    "image": image_url,
                    "end_date": end_date_str
                })
                
        return free_games
        
    except Exception as e:
        print(f"获取 Epic 数据出错: {e}")
        return []

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ 错误：未设置 Token 或 Chat ID")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML", 
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload)
        print("✅ 消息推送成功")
    except Exception as e:
        print(f"❌ 推送错误: {e}")

if __name__ == "__main__":
    print("⏳ 开始检查 Epic 免费游戏 (精准中文版)...")
    games = get_epic_free_games()
    
    if games:
        print(f"🎉 发现 {len(games)} 个免费游戏")
        for g in games:
            safe_title = g['title'] # 已经是安全的 HTML
            safe_desc = html.escape(g['description'])
            
            msg = (
                f"<a href='{g['image']}'>&#8205;</a>"
                f"🔥 <b>Epic 喜加一提醒</b> 🔥\n\n"
                f"🎮 <b>{safe_title}</b>\n"
                f"⏰ 截止: {g['end_date']}\n\n"
                f"📝 {safe_desc}\n\n"
                f"🔗 <a href='{g['link']}'>点击领取游戏</a>"
            )
            send_telegram_message(msg)
    else:
        print("🤷‍♂️ 当前没有检测到免费游戏")
