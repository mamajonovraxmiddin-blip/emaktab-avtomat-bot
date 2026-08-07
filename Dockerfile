# 1. Playwright brauzerlari oldindan o'rnatilgan tayyor rasmiy Python imijini olamiz
FROM ://microsoft.com

# 2. Server ichida ishchi papka yaratamiz
WORKDIR /app

# 3. Kutubxonalar ro'yxatini serverga nusxalaymiz va o'rnatamiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Loyihadagi barcha fayllarni serverga nusxalaymiz
COPY . .

# 5. Botni ishga tushirish buyrug'i
CMD ["python", "bot.py"]
