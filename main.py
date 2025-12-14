import requests
import os

# 从 GitHub Secrets 获取配置
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
CHAT_ID = os.environ.get("TG_CHAT_ID")

def get_epic_free_games():
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    try:
        res = requests.get(url).json()
        games = res['data']['Catalog']['searchStore']['elements']
        
        free_games = []
        for game in games:
            promotions = game.get('promotions')
            if not promotions:
                continue
            
            # 检查是否有当前促销
            if not promotions.get('promotionalOffers'):
                continue
            
            offers = promotions['promotionalOffers']
            if not offers:
                continue

            is_free = False
            for offer_group in offers:
                for offer in offer_group['promotionalOffers']:
                    if offer['discountSetting']['discountPercentage'] == 0:
                        is_free = True
                        
            if is_free:
                title = game.get('title')
                description = game.get('description', '暂无描述')
                # 拼接下载链接 (通常是 epicgames.com/p/游戏名-slug)
                slug = game.get('productSlug') or game.get('urlSlug')
                link = f"https://store.epicgames.com/p/{slug}" if slug else "https://store.epicgames.com/free-games"
                
                free_games.append({
                    "title": title,
                    "description": description,
                    "link": link
                })
        return free_games
    except Exception as e:
        print(f"Error: {e}")
        return []

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("未设置 Token 或 Chat ID")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown", # 允许简单的格式化
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    print("正在检查 Epic 免费游戏...")
    games = get_epic_free_games()
    
    if games:
        # 构建消息内容
        msg_lines = ["🔥 **Epic 本周免费游戏** 🔥"]
        for g in games:
            msg_lines.append(f"\n🎮 **{g['title']}**")
            msg_lines.append(f"📝 {g['description']}")
            msg_lines.append(f"🔗 [点击领取]({g['link']})")
        
        full_msg = "\n".join(msg_lines)
        send_telegram_message(full_msg)
        print("推送成功！")
    else:
        print("未发现免费游戏或接口变动。")
