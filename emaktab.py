import os
import asyncio
import aiohttp

# 2Captcha xizmati uchun API kalitni tizim muhitidan olamiz
CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY")

async def solve_captcha_async(session, image_bytes):
    """
    2Captcha xizmati orqali rasmli kapchani butunlay asinxron yechish funksiyasi.
    Bu funksiya asosiy kod bloklanishini (muzlashini) oldini oladi.
    """
    try:
        # 1. Kapcha rasmini yuborish uchun ma'lumotlarni tayyorlaymiz
        data = aiohttp.FormData()
        data.add_field('key', CAPTCHA_API_KEY)
        data.add_field('method', 'post')
        data.add_field('json', '1')
        data.add_field('file', image_bytes, filename='captcha.png', content_type='image/png')
        
        # 2Captcha serveriga rasmni yuklaymiz
        async with session.post("https://2captcha.com", data=data, timeout=12) as resp:
            submit_res = await resp.json()
            
        if submit_res.get("status") != 1:
            return None
            
        # Yuklangan kapchaning maxsus ID raqamini olamiz
        captcha_id = submit_res.get("request")
        
        # 2. Tayyor javobni olish uchun asinxron tekshirish sikli (har 3 soniyada)
        for _ in range(15):
            await asyncio.sleep(3)
            url = f"https://2captcha.com{CAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1"
            async with session.get(url, timeout=10) as resp:
                res = await resp.json()
            
            # Agar kapcha muvaffaqiyatli yechilgan bo'lsa, matnni qaytaramiz
            if res.get("status") == 1:
                return res.get("request")
                
        return None
    except Exception:
        return None

async def try_emaktab_login(login, password):
    """
    eMaktab.uz tizimiga login va parol orqali kirishni tekshiruvchi asosiy funksiya.
    Hech qanday og'ir brauzerlarsiz (Playwright-siz), eng tezkor HTTP so'rovlar yordamida ishlaydi.
    """
    try:
        # Haqiqiy brauzer kabi ko'rinish uchun sarlavhalar (Headers)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'uz,ru;q=0.9,en;q=0.8'
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            # Kirish uchun aniq manzil
            login_url = "https://emaktab.uz" 
            
            # eMaktab asosiy login sahifasini ochamiz
            async with session.get(login_url, timeout=15) as resp:
                main_page_text = await resp.text()
            
            # Tizimga yuboriladigan foydalanuvchi ma'lumotlari
            payload = {
                'login': login,
                'password': password
            }
            
            # Agar eMaktab sahifasida kapcha himoyasi aniqlansa
            if 'captcha' in main_page_text or 'captcha-image' in main_page_text:
                # Haqiqiy kapcha rasmining yuklanish havolasi
                captcha_img_url = "https://emaktab.uzcaptcha.ashx"
                async with session.get(captcha_img_url, timeout=10) as img_resp:
                    img_bytes = await img_resp.read()
                
                # Kapchani yechishga yuboramiz
                captcha_code = await solve_captcha_async(session, img_bytes)
                if not captcha_code:
                    return "❌ Sayt kapcha so'radi, lekin 2Captcha uni yechishda xatolik berdi."
                
                # eMaktab tizimi talab qiladigan maydon nomiga kodni yozamiz
                payload['Captcha.Input'] = captcha_code 
                
            # Ma'lumotlarni POST so'rovi orqali eMaktab serveriga jo'natamiz
            async with session.post(login_url, data=payload, timeout=15, allow_redirects=True) as post_resp:
                final_url = str(post_resp.url)
                final_text = await post_resp.text()
            
            # Kirish muvaffaqiyatli bo'lganini tekshiramiz (Xatolik so'zi chiqmasa va sahifa o'zgarsa)
            if post_resp.status == 200 and "Xato" not in final_text and "login" not in final_url:
                return "✅ Tizimga muvaffaqiyatli kirildi!"
            else:
                return "❌ Kirib bo'lmadi! Login yoki parol noto'g'ri."
                
    except Exception as e:
        return f"⚠️ Tizimga ulanishda kutilmagan xatolik: {str(e)}"
