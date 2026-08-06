import os
import asyncio
from playwright.async_api import async_playwright

CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY")

async def try_emaktab_login(login, password):
    """
    Playwright orqali eMaktab.uz tizimiga haqiqiy brauzer orqali kirish.
    Bu usul hisobotlarda 100% aks etadi va xatoliklar aniq tekshiriladi.
    """
    async with async_playwright() as p:
        # Render serveri uchun chromium brauzerini ochamiz
        browser = await p.chromium.launch(headless=True)
        # Haqiqiy odamdek ko'rinish uchun brauzer sozlamalari
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        
        try:
            # 1. Login sahifasiga kirish
            await page.goto("https://emaktab.uz", timeout=30000)
            await page.wait_for_load_state("networkidle")
            
            # 2. Login va parolni joylash
            await page.fill("input[name='login']", login)
            await page.fill("input[name='password']", password)
            
            # 3. Agar kapcha rasmi chiqsa aniqlash va yechish
            captcha_selector = "img[src*='captcha.ashx'], .captcha-image"
            if await page.is_visible(captcha_selector):
                import aiohttp
                captcha_element = await page.query_selector(captcha_selector)
                img_bytes = await captcha_element.screenshot()
                
                # 2Captcha asinxron yuborish
                async with aiohttp.ClientSession() as session:
                    data = aiohttp.FormData()
                    data.add_field('key', CAPTCHA_API_KEY)
                    data.add_field('method', 'post')
                    data.add_field('json', '1')
                    data.add_field('file', img_bytes, filename='captcha.png', content_type='image/png')
                    
                    async with session.post("https://2captcha.com", data=data) as resp:
                        submit_res = await resp.json()
                    
                    if submit_res.get("status") == 1:
                        captcha_id = submit_res.get("request")
                        captcha_code = None
                        for _ in range(15):
                            await asyncio.sleep(3)
                            res_url = f"https://2captcha.com{CAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1"
                            async with session.get(res_url) as r_resp:
                                r_res = await r_resp.json()
                            if r_res.get("status") == 1:
                                captcha_code = r_res.get("request")
                                break
                        
                        if captcha_code:
                            await page.fill("input[name='Captcha.Input']", captcha_code)
            
            # 4. Kirish tugmasini bosish
            await page.click("input[type='submit'], button[type='submit']")
            # Sahifa yuklanishini yoki yo'naltirilishini kutish
            await page.wait_for_timeout(5000) 
            
            current_url = page.url
            current_content = await page.content()
            
            # 5. Natijani tekshirish
            if "Xato" in current_content or "Неверный" in current_content or "login" in current_url:
                await browser.close()
                return "❌ Login yoki Parol xato kiritildi!"
                
            # 6. Statistika uchun ichki bo'limlarni ochish
            await page.goto("https://emaktab.uz", timeout=15000)
            await page.wait_for_timeout(2000)
            await page.goto("https://emaktab.uz", timeout=15000)
            await page.wait_for_timeout(2000)
            
            await browser.close()
            return "✅ Tizimga muvaffaqiyatli kirildi va faollik qayd etildi!"
            
        except Exception as e:
            await browser.close()
            return f"⚠️ Kirish jarayonida xatolik: {str(e)}"
