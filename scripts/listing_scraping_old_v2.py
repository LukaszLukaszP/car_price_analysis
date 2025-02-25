import os
import time
import random
import pandas as pd
import undetected_chromedriver as uc
import psutil
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from selenium_stealth import stealth
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# 📌 SELENIUM CONFIGURATION (Without using undetected_chromedriver)
options = Options()
options.add_argument("--headless=new")  # ✅ Headless mode (new version)
options.add_argument("--disable-blink-features=AutomationControlled")  # ✅ Hides Selenium usage
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

service = Service("C:/WINDOWS/system32/chromedriver.exe")  # Path to chromedriver
driver = webdriver.Chrome(service=service, options=options)

# ✅ Hiding Selenium property (Bot-detection bypass)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# 📌 MASKING BOT CHARACTERISTICS (using selenium-stealth)
stealth(driver,
    languages=["pl-PL", "pl"],
    vendor="Google Inc.",
    platform="Win32",
    webgl_vendor="Intel Inc.",
    renderer="Intel Iris OpenGL Engine",
    fix_hairline=True,
)

# 📌 BASE URL
base_url = "https://www.otomoto.pl/osobowe?search%5Bfilter_enum_damaged%5D=0&search%5Badvanced_search_expanded%5D=true"

# 📌 SCRAPING 2 PAGES (for testing)
all_data = []
for page in range(1, 3):
    page_url = f"{base_url}&page={page}"
    print(f"🔄 Scraping: {page_url}")

    driver.get(page_url)
    time.sleep(random.uniform(5, 10))  # ✅ Random delays to avoid detection

    # 📌 Save the retrieved HTML to verify that Selenium is fetching the correct page
    page_source = driver.page_source
    with open(f"otomoto_page_{page}.html", "w", encoding="utf-8") as f:
        f.write(page_source)

    # 📌 Parsing the page
    soup = BeautifulSoup(page_source, "html.parser")

    offers = soup.find_all("article", {"data-id": True})

    if not offers:
        print(f"⚠️ No listings found on page {page_url}. Check otomoto_page_{page}.html")

    for offer in offers:
        try:
            listing_id = offer.get("data-id", "N/A")

            title_tag = offer.find("h2")
            title = title_tag.text.strip() if title_tag else "N/A"

            link_tag = title_tag.find("a") if title_tag else None
            link = link_tag["href"] if link_tag else "N/A"

            price_tag = offer.find("h3")
            price = price_tag.text.strip().replace(" ", "") if price_tag else "N/A"

            currency_tag = offer.find("p")
            currency = currency_tag.text.strip() if currency_tag and any(c in currency_tag.text for c in ["PLN", "EUR", "$"]) else "N/A"

            all_data.append({
                "ID": listing_id,
                "Title": title,
                "Price": price,
                "Currency": currency,
                "Link": link
            })
        except Exception as e:
            print(f"Error: {e}")

# 📌 SAVING TO CSV
if all_data:
    df = pd.DataFrame(all_data)
    df.to_csv("otomoto_test_ai_agent.csv", index=False)
    print("✅ Scraping completed! Data saved to otomoto_test_ai_agent.csv")
else:
    print("❌ No data to save. Check the files `otomoto_page_1.html` and `otomoto_page_2.html`.")

# 📌 GRACEFULLY CLOSING THE BROWSER
try:
    driver.quit()  # ✅ Close Selenium if it's running
    time.sleep(2)  # ✅ Allow time for the process to fully close
except Exception as e:
    print(f"⚠️ Issue closing Selenium: {e}")
finally:
    for proc in psutil.process_iter():
        if "chrome" in proc.name().lower():
            try:
                proc.kill()  # ✅ Forcefully terminate the Chrome process if it's still running
            except psutil.NoSuchProcess:
                pass

print("✅ Script finished successfully!")
