import os
import asyncio
import aiohttp
from playwright.async_api import async_playwright

CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY")

# Asinxron kapcha yechish funksiyasi
async def solve_captcha_async(image_bytes):
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('key', CAPTCHA_API_KEY)
            data.add_field('method', 'post')
            data.add_field('json', '1')
            data.add_field('file', image_bytes, filename='captcha.png', content_type='image/png')
            
            async with session.post("https://2captcha.com", data=data, timeout=10) as resp:
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

# eMaktab.uz tizimiga Haqiqiy Brauzer orqali kirish (O'sha siz aytgan ilk eng barqaror kod)
async def try_emaktab_login(login, password):
    try:
        async with async_playwright() as p:
            # Brauzerni hech qanday sun'iy taqiqlarsiz, standart rejimda ochamiz
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # 1. Kirish sahifasini ochish
            await page.goto("https://emaktab.uz", timeout=30000)
            
            # 2. Ma'lumotlarni kiritish
            await page.fill('input[name="login"]', login)
            await page.fill('input[name="password"]', password)
            
            # 3. Kapcha borligini tekshirish
            captcha_element = await page.query_selector('img[id="captcha-image"]') or await page.query_selector('.captcha-image')
            if captcha_element:
                img_bytes = await captcha_element.screenshot()
                captcha_code = await solve_captcha_async(img_bytes)
                if captcha_code:
                    await page.fill('input[name="captcha"]', captcha_code)
            
            # 4. Kirish tugmasini bosish
            await page.click('input[type="submit"]')
            
            # Sahifa to'liq yuklanishini va tizim sessiya olishini 5 soniya kutamiz (Hisobotlar uchun muhim)
            await page.wait_for_timeout(5000)
            
            current_url = page.url
            page_content = await page.content()
            await browser.close()
            
            # 5. Kirish holatini tekshirish zanjiri
            if "login" in current_url or "Xato" in page_content or "not-found" in current_url:
                return "❌ Kirib bo'lmadi! Login yoki parol xato kiritilgan."
            else:
                return "✅ Tizimga muvaffaqiyatli kirildi!"
                
    except Exception as e:
        return f"⚠️ Tizimga ulanishda kutilmagan xatolik: {str(e)}"
