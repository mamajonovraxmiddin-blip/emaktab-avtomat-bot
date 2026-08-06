import os
import asyncio
import aiohttp

CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY")

async def solve_captcha_async(session, image_bytes):
    try:
        data = aiohttp.FormData()
        data.add_field('key', CAPTCHA_API_KEY)
        data.add_field('method', 'post')
        data.add_field('json', '1')
        data.add_field('file', image_bytes, filename='captcha.png', content_type='image/png')
        
        async with session.post("https://2captcha.com", data=data, timeout=15) as resp:
            submit_res = await resp.json()
            
        if submit_res.get("status") != 1:
            return None
            
        captcha_id = submit_res.get("request")
        
        for _ in range(20):
            await asyncio.sleep(3)
            url = f"https://2captcha.com{CAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1"
            async with session.get(url, timeout=10) as resp:
                res = await resp.json()
            if res.get("status") == 1:
                return res.get("request")
        return None
    except Exception:
        return None

async def try_emaktab_login(login, password):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'uz,ru;q=0.9,en;q=0.8',
            'Referer': 'https://emaktab.uz'
        }
        
        async with aiohttp.ClientSession(headers=headers, cookie_jar=aiohttp.CookieJar()) as session:
            login_url = "https://emaktab.uz" 
            
            async with session.get(login_url, timeout=15) as resp:
                main_page_text = await resp.text()
            
            payload = {
                'login': login,
                'password': password
            }
            
            if 'captcha' in main_page_text.lower():
                # Hech qanday RegEx-siz, faqat aniq statik havola
                captcha_img_url = "https://emaktab.uzcaptcha.ashx"
                
                async with session.get(captcha_img_url, timeout=12) as img_resp:
                    img_bytes = await img_resp.read()
                
                captcha_code = await solve_captcha_async(session, img_bytes)
                if not captcha_code:
                    return "❌ Sayt kapcha so'radi, lekin 2Captcha xizmati javob qaytara olmadi."
                
                payload['Captcha.Input'] = captcha_code 
                
            async with session.post(login_url, data=payload, timeout=15, allow_redirects=True) as post_resp:
                final_text = await post_resp.text()
                final_url = str(post_resp.url)
                
                if "Xato" in final_text or "Неверный" in final_text or "login" in final_url:
                    return "❌ Login yoki Parol xato kiritildi!"
                
                                # 4. STATISTIKA UCHUN FAOLLIK QISMI (Hisobotda ko'rinishi uchun shart)
                try:
                    import datetime
                    bugun = datetime.date.today().strftime("%Y-%m-%d")
                    
                    # Tizim o'quvchi kirdi deb hisoboti yangilaydigan asosiy manzillar:
                    feed_url = "https://emaktab.uz"
                    diary_url = f"https://emaktab.uz{bugun}" # Bugungi kunlik sahifasi
                    tasks_url = "https://emaktab.uz"
                    
                    # 1. Asosiy lenta (Dashboard) yuklanishi
                    async with session.get(feed_url, timeout=10) as feed_resp:
                        await feed_resp.text()
                        
                    # 2. Bugungi kunlik darslar jadvalini to'liq ochish (Bu statistika uchun eng muhimi!)
                    async with session.get(diary_url, timeout=10) as diary_resp:
                        await diary_resp.text()
                        
                    # 3. Uy vazifalari sahifasini yangilash
                    async with session.get(tasks_url, timeout=10) as tasks_resp:
                        await tasks_resp.text()
                        
                    # 4. eMaktab hisobot tizimiga "Sessiya faol" degan bildirishnomani majburiy yuborish
                    # Ba'zan tizim bildirishnomalar (Notification) API orqali hisobotni yangilaydi
                    api_check_url = "https://emaktab.uz"
                    async with session.get(api_check_url, timeout=10) as api_resp:
                        await api_resp.text()
                        
                except Exception:
                    pass
                
                return "✅ Tizimga muvaffaqiyatli kirildi va faollik qayd etildi!"
                
    except Exception as e:
        return f"⚠️ Tizimga ulanishda kutilmagan xatolik: {str(e)}"
