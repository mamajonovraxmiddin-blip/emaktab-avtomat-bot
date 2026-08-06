import os
import requests

CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY")

# 2Captcha orqali rasmli kapchani matnga aylantirish
def solve_captcha_requests(session):
    try:
        captcha_url = "https://emaktab.uz"
        response = session.get(captcha_url, timeout=10)
        
        files = {'file': ('captcha.png', response.content, 'image/png')}
        payload = {
            'key': CAPTCHA_API_KEY,
            'method': 'post',
            'json': 1
        }
        
        submit_res = requests.post("https://2captcha.com", data=payload, files=files, timeout=10).json()
        if submit_res.get("status") != 1:
            return None
            
        captcha_id = submit_res.get("request")
        
        # Kapcha javobini 15 soniya davomida poylash
        import time
        for _ in range(10):
            time.sleep(3)
            res = requests.get(f"https://2captcha.com{CAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1", timeout=10).json()
            if res.get("status") == 1:
                return res.get("request")
        return None
    except Exception:
        return None

# Brauzersiz, eng tezkor requests.Session aloqasi
async def try_emaktab_login(login, password):
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'uz,ru;q=0.9,en;q=0.8'
        })
        
        login_url = "https://emaktab.uz"
        
        # 1. Kirish sahifasini tekshirish
        main_page = session.get(login_url, timeout=15)
        
        payload = {
            'login': login,
            'password': password
        }
        
        # Agar sahifada kapcha elementi aniqlansa
        if 'captcha' in main_page.text or 'captcha-image' in main_page.text:
            captcha_code = solve_captcha_requests(session)
            if not captcha_code:
                return "❌ Sayt kapcha so'radi, lekin 2Captcha uni yechishda xatolik berdi."
            payload['captcha'] = captcha_code
            
        # 2. Login so'rovini brauzersiz to'g'ridan-to'g'ri yuborish
        res = session.post(login_url, data=payload, timeout=15)
        
        # Profil sahifasiga muvaffaqiyatli yo'naltirilganini (Sessiya faolligini) tekshirish
        if res.status_code == 200 and "Xato" not in res.text and "login" not in res.url:
            return "✅ Tizimga muvaffaqiyatli kirildi!"
        else:
            return "❌ Kirib bo'lmadi! Login yoki parol noto'g'ri."
            
    except Exception as e:
        return f"⚠️ Tizimga ulanishda kutilmagan xatolik: {str(e)}"
