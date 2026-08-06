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
        
        async with session.post("https://2captcha.com", data=data, timeout=12) as resp:
            submit_res = await resp.json()
            
        if submit_res.get("status") != 1:
            return None
            
        captcha_id = submit_res.get("request")
        
        for _ in range(15):
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'uz,ru;q=0.9,en;q=0.8'
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            login_url = "https://login.emaktab.uz/" 
            
            async with session.get(login_url, timeout=15) as resp:
                main_page_text = await resp.text()
            
            payload = {
                'login': login,
                'password': password
            }
            
            if 'captcha' in main_page_text or 'captcha-image' in main_page_text:
                captcha_img_url = "https://emaktab.uz"
                async with session.get(captcha_img_url, timeout=10) as img_resp:
                    img_bytes = await img_resp.read()
                
                captcha_code = await solve_captcha_async(session, img_bytes)
                if not captcha_code:
                    return "❌ Sayt kapcha so'radi, lekin 2Captcha uni yechishda xatolik berdi."
                payload['Captcha.Input'] = captcha_code 
                
            # POST so'rovi yuborilganda allow_redirects=False qilamiz.
            # Chunki login TO'G'RI bo'lsa, eMaktab foydalanuvchini boshqa sahifaga (302 Redirect) otib yuboradi.
            # Login XATO bo'lsa, xuddi shu login sahifasining o'zida olib qoladi (200 OK).
            async with session.post(login_url, data=payload, timeout=15, allow_redirects=False) as post_resp:
                
                # 1-Holat: Agar xato bo'lsa (Sahifa o'zgarmaydi va status 200 qaytadi)
                if post_resp.status == 200:
                    return "❌ Login yoki Parol xato kiritildi!"
                
                # 2-Holat: Agar to'g'ri bo'lsa (Tizim boshqa sahifaga yo'naltiradi, status 302 yoki 301 bo'ladi)
                elif post_resp.status in [301, 302]:
                    
                    # ----------------- STATISTIKA UCHUN FAOLLIK QISMI -----------------
                    # Tizim hisobotlarida kirish qayd etilishi uchun ichki sahifalarga so'rov yuboramiz
                    try:
                        feed_url = "https://emaktab.uz"
                        diary_url = "https://emaktab.uz"
                        
                        async with session.get(feed_url, timeout=10) as feed_resp:
                            await feed_resp.text()
                            
                        async with session.get(diary_url, timeout=10) as diary_resp:
                            await diary_resp.text()
                    except Exception:
                        pass
                    # -----------------------------------------------------------------
                    
                    return "✅ Tizimga muvaffaqiyatli kirildi va faollik qayd etildi!"
                
                else:
                    return "❌ Kirib bo'lmadi! Noma'lum xatolik yuz berdi."
                
    except Exception as e:
        return f"⚠️ Tizimga ulanishda kutilmagan xatolik: {str(e)}"
