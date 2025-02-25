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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 📌 SELENIUM CONFIGURATION
options = Options()
options.add_argument("--headless=new")  # ✅ Headless mode (new version)
options.add_argument("--disable-blink-features=AutomationControlled")  # ✅ Hides Selenium detection
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

# 📌 INITIALIZING SELENIUM
service = Service("C:/WINDOWS/system32/chromedriver.exe")  # Ensure the chromedriver path is correct
driver = webdriver.Chrome(service=service, options=options)

# ✅ Hiding Selenium from detection
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
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

# Wait for the page to load by waiting until an element with 'article[data-id]' is present.
def wait_for_page_load(driver, timeout=6):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-id]"))
    )

# 📌 FUNCTION TO DETECT HTML SELECTORS
def detect_selectors(url):
    """Detects the current HTML selectors for Otomoto listings."""
    driver.get(url)
    time.sleep(random.uniform(5, 10))  # ✅ Delay for safety
    page_source = driver.page_source

    # 📌 Save the HTML to a file for debugging
    with open("otomoto_sample.html", "w", encoding="utf-8") as f:
        f.write(page_source)

    soup = BeautifulSoup(page_source, "html.parser")

    # 🔍 Look for the first listing
    first_offer = soup.find("article", {"data-id": True})
    if not first_offer:
        print("❌ No listings found on the page! Check the file `otomoto_sample.html`")
        return {}

    selectors = {}

    # 🔍 Listing ID
    selectors["listing_id"] = "article[data-id]"

    # 🔍 Title and link
    title_tag = first_offer.find("h2")
    if title_tag and title_tag.find("a"):
        selectors["title"] = "h2 a"
        selectors["link"] = "h2 a"

    # 🔍 Price
    price_tag = first_offer.find("h3")
    if price_tag:
        selectors["price"] = "h3"

    # 🔍 Currency (detected by text PLN/EUR)
    selectors["currency"] = "p"

    # 🔍 Description
    description_tag = first_offer.find("p")
    if description_tag:
        selectors["description"] = "p"

    # 🔍 Technical parameters (mileage, fuel type, gearbox, year)
    for param in ["mileage", "fuel_type", "gearbox", "year"]:
        param_tag = first_offer.find("dd", {"data-parameter": param})
        if param_tag:
            selectors[param] = f"dd[data-parameter='{param}']"

    # 🔍 Location
    location_tag = first_offer.select_one("dl p")
    if location_tag:
        selectors["location"] = "dl p"

    # 🔍 Seller type
    seller_tag = first_offer.select_one("article li")
    if seller_tag:
        selectors["seller_type"] = "article li"

    # 🔍 Otomoto indicator (e.g., "Within average range")
    indicator_tag = first_offer.select_one("p")
    if indicator_tag:
        selectors["otomoto_indicator"] = "p"

    print(f"✅ Detected selectors: {selectors}")
    return selectors

# 📌 DETECT SELECTORS BEFORE SCRAPING
selectors = detect_selectors(base_url)
if not selectors:
    print("❌ Selectors not detected! Stopping the script.")
    driver.quit()
    exit()

# 📌 SCRAPING PAGES
all_data = []
for page in range(1, 3):  # Testing only 2 pages
    page_url = f"{base_url}&page={page}"
    print(f"🔄 Scraping: {page_url}")

    driver.get(page_url)
    # time.sleep(random.uniform(3, 6))  # ✅ Random delay
    wait_for_page_load(driver, timeout=6)

    # 📌 Retrieve HTML and parse it
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "html.parser")
    offers = soup.find_all("article", {"data-id": True})

    if not offers:
        print(f"⚠️ No listings found on {page_url}. Check `otomoto_page_{page}.html`.")
        continue

    for offer in offers:
        try:
            listing_id = offer.get("data-id", "N/A")

            title_element = offer.select_one(selectors.get("title", "h2 a"))
            title = title_element.text.strip() if title_element else "N/A"

            link_element = offer.select_one(selectors.get("link", "h2 a"))
            link = link_element["href"] if link_element else "N/A"

            price_element = offer.select_one(selectors.get("price", "h3"))
            price = price_element.text.strip().replace(" ", "") if price_element else "N/A"

            # 🔍 Searching for currency based on text (PLN/EUR)
            currency_element = offer.find("p", string=lambda text: text and ("PLN" in text or "EUR" in text))
            currency = currency_element.text.strip() if currency_element else "N/A"

            description_element = offer.select("p")  # Retrieve all 'p' elements
            description = "N/A"

            for p in description_element:
                text = p.text.strip()
                if "cm3" in text or "KM" in text:  # Check if text looks like a technical description
                    description = text
                    break

            mileage_element = offer.select_one(selectors.get("mileage", "dd[data-parameter='mileage']"))
            mileage = mileage_element.text.strip() if mileage_element else "N/A"

            fuel_type_element = offer.select_one(selectors.get("fuel_type", "dd[data-parameter='fuel_type']"))
            fuel_type = fuel_type_element.text.strip() if fuel_type_element else "N/A"

            gearbox_element = offer.select_one(selectors.get("gearbox", "dd[data-parameter='gearbox']"))
            gearbox = gearbox_element.text.strip() if gearbox_element else "N/A"

            year_element = offer.select_one(selectors.get("year", "dd[data-parameter='year']"))
            year = year_element.text.strip() if year_element else "N/A"

            location_element = offer.select_one(selectors.get("location", "dl p"))
            location = location_element.text.strip() if location_element else "N/A"

            seller_type_element = offer.select_one(selectors.get("seller_type", "article li"))
            seller_type = seller_type_element.text.strip() if seller_type_element else "N/A"

            indicator_element = offer.find("p", string=lambda text: text and "średniej" in text)  # Look for text indicating an average price
            indicator = indicator_element.text.strip() if indicator_element else "N/A"

            all_data.append({
                "ID": listing_id,
                "Title": title,
                "Link": link,
                "Description": description,
                "Mileage": mileage,
                "Fuel Type": fuel_type,
                "Gearbox": gearbox,
                "Year": year,
                "Location": location,
                "Seller Type": seller_type,
                "Price": price,
                "Currency": currency,
                "Otomoto Indicator": indicator                
            })
        except Exception as e:
            print(f"Error: {e}")

# 📌 SAVE TO CSV
if all_data:
    df = pd.DataFrame(all_data)
    df.to_csv("data/otomoto_test_ai_agent.csv", index=False)
    print("✅ Scraping completed! Data saved to otomoto_test_ai_agent.csv")
else:
    print("❌ No data to save. Check the file `otomoto_sample.html`.")

# 📌 GRACEFULLY CLOSE THE BROWSER
try:
    driver.quit()
    time.sleep(2)  # ✅ Allow time for the process to fully terminate
except Exception as e:
    print(f"⚠️ Issue closing Selenium: {e}")
finally:
    for proc in psutil.process_iter():
        if "chrome" in proc.name().lower():
            try:
                proc.kill()  # ✅ Forcefully terminate Chrome process if still running
            except psutil.NoSuchProcess:
                pass

print("✅ Script finished successfully!")
