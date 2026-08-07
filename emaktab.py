import asyncio
import logging
import os
import aiohttp
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TWOCAPTCHA_API_KEY = os.getenv("TWOCAPTCHA_API_KEY")

async def solve_recaptcha(site_key, page_url):
    """eMaktab kapchasini hal qilish"""
    if not TWOCAPTCHA_API_KEY:
        logger.error("2Captcha API kaliti topilmadi")
        return None
        
    async with aiohttp.ClientSession() as session:
        params = {
            'key': TWOCAPTCHA_API_KEY,
            'method': 'userrecaptcha',
            'googlekey': site_key,
            'pageurl': page_url,
            'json': 1
        }
        try:
            async with session.post("http://2captcha.com", data=params) as resp:
                res = await resp.json()
                if res.get('status') != 1:
                    return None
                request_id = res.get('request')

            for _ in range(24):
                await asyncio.sleep(5)
                async with session.get(f"http://2captcha.com{TWOCAPTCHA_API_KEY}&action=get&id={request_id}&json=1") as resp:
                    res = await resp.json()
                    if res.get('status') == 1:
                        return res.get('request')
        except Exception as e:
            logger.error(f"2Captcha xatosi: {e}")
    return None

async def run_emaktab_login(username, password):
    """Orqa fonda original tezlikda brauzer orqali kirish va aniq xatoliklarni ajratish"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # 1. Tizimga ulanish (Internet muammosini tekshirish)
            try:
                await page.goto("https://login.emaktab.uz/", wait_until="networkidle", timeout=20000)
            except Exception:
                await browser.close()
                return {"status": False, "message": "Internet muammosi mavjud, aloqani tekshiring"}
            
            # Ma'lumotlarni kiritish
            await page.fill("input[name='login']", str(username))
            await page.fill("input[name='password']", str(password))
            
            # 2. Kapcha so'ralganligini tekshirish
            captcha_element = await page.query_selector(".g-recaptcha")
            if captcha_element:
                site_key = await captcha_element.get_attribute("data-sitekey")
                captcha_token = await solve_recaptcha(site_key, page.url)
                if captcha_token:
                    await page.evaluate(f'document.getElementById("g-recaptcha-response").innerHTML="{captcha_token}";')
                else:
                    await browser.close()
                    return {"status": False, "message": "Kapcha yechishda muammo yuz berdi"}

            # Kirish tugmasini bosish
            await page.click("input[type='submit']")
            
            # KAFOLAT: Sahifa yo'naltirilishini (Redirect) yoki to'liq yuklanishini kutamiz
            await page.wait_for_load_state("networkidle")

            # 3. Brauzer joriy URL manzilini tekshirish (Eng aniq usul)
            current_url = page.url
            
            # Agar URL o'zgargan bo'lsa va login.emaktab.uz dan chiqib ketgan bo'lsa - kirish 100% muvaffaqiyatli
            if "login.emaktab.uz" not in current_url or "desktop" in current_url or "feed" in current_url:
                await browser.close()
                return {"status": True, "message": "Tizimga muvaffaqiyatli kirildi (Hisobot qayd etildi)."}

            # 4. Agar hali ham login sahifasida bo'lsa, xatolik xabarini tekshiramiz
            error_message = await page.query_selector(".error, .validation-summary-errors, .alert-danger")
            if error_message:
                await browser.close()
                return {"status": False, "message": "Login yoki parol noto'g'ri kritilgan"}

            # Kutilmagan boshqa holat yuz bersa
            await browser.close()
            return {"status": False, "message": "Login yoki parol noto'g'ri kritilgan"}

        except Exception as e:
            await browser.close()
            return {"status": False, "message": f"Texnik nosozlik yuz berdi: {str(e)}"}
