import requests
import os
from datetime import datetime
import html  # 用于转义 HTML 特殊字符

# 1. 获取 GitHub Secrets
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
CHAT_ID = os.environ.get("TG_CHAT_ID")

def get_epic_free_games():
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    try:
        res = requests.get(url).json()
        games = res['data']['Catalog']['searchStore']['elements']
        
        free_games = []
        for game in games:
            # 1. 基础过滤：必须有促销信息
            promotions = game.get('promotions')
            if not promotions:
                continue
            
            if not promotions.get('promotionalOffers'):
                continue
            
            # 【注意】我注释掉了 offerType 过滤，防止霍格沃茨被误杀
            # offer_type = game.get('offerType')
            # if offer_type and offer_type != 'BASE_GAME':
            #     continue

            # 2. 检查价格是否为 0
            offers = promotions['promotionalOffers']
            if not offers:
                continue

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
                title = game.get('title')
                description = game.get('description', '暂无描述')
                slug = game.get('productSlug') or game.get('urlSlug')
                link = f"https://store.epicgames.com/p/{slug}" if slug else "https://store.epicgames.com/free-games"
                
                image_url = ""
                for img in game.get('keyImages', []):
                    if img.get('type') == 'Thumbnail':
                        image_url = img.get('url')
                        break
                    elif img.get('type') == 'OfferImageWide':
                        image_url = img.get('url')

                free_games.append({
                    "title": title,
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
        "parse_mode": "HTML",  # 【关键修改】改用 HTML 模式，更稳定
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            print("✅ 消息推送成功")
        else:
            print(f"❌ 推送失败: {res.text}")
    except Exception as e:
        print(f"❌ 请求错误: {e}")

if __name__ == "__main__":
    print("⏳ 开始检查 Epic 免费游戏...")
    games = get_epic_free_games()
    
    if games:
        print(f"🎉 发现 {len(games)} 个免费游戏")
        for g in games:
            # HTML 格式构建消息，使用 html.escape 防止描述里的 < > & 符号搞坏格式
            safe_title = html.escape(g['title'])
            safe_desc = html.escape(g['description'])
            
            # <a href="...">&#8205;</a> 是插入不可见字符用来显示图片预览的技巧
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
        print("🤷‍♂️ 当前没有检测到免费游戏 (或接口变动)")
