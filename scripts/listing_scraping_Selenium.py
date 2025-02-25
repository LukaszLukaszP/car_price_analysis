import os
from datetime import datetime
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =====================================
# ADDITIONAL IMPROVEMENT FUNCTIONS
# =====================================

# List of sample User-Agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0_1) AppleWebKit/535.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/535.36",
]

def rotate_user_agent(index=None):
    """
    Returns a random or cyclic User-Agent from the list.
    """
    if index is not None:
        return USER_AGENTS[index % len(USER_AGENTS)]
    else:
        return random.choice(USER_AGENTS)

def is_captcha_page(soup):
    """
    Checks if the page contains a message indicating a block (captcha or "too many requests").
    """
    text = soup.get_text().lower()
    if "captcha" in text or "zbyt wiele zapytań" in text:
        return True
    return False

def create_unique_key(car):
    """
    Creates a unique key for a car offer based on selected fields.
    """
    fields = [
        car.get('Title', ''),
        car.get('Description', ''),
        car.get('Mileage', ''),
        car.get('Fuel Type', ''),
        car.get('Gearbox', ''),
        car.get('Year', ''),
        car.get('Location', ''),
        car.get('Seller Type', ''),
        car.get('Price', ''),
    ]
    fields = [str(x).strip() for x in fields]
    return "|".join(fields)

# =====================================
# SELENIUM CONFIGURATION
# =====================================

options = Options()
options.add_argument("--headless=new")  # Run in headless mode (new version)
options.add_argument("--disable-blink-features=AutomationControlled")  # Hide Selenium usage
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
# (Optionally, proxy settings can be added if available)

service = Service("C:/WINDOWS/system32/chromedriver.exe")  # Ensure the path is correct
driver = webdriver.Chrome(service=service, options=options)

# Hide Selenium from detection
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
stealth(driver,
    languages=["pl-PL", "pl"],
    vendor="Google Inc.",
    platform="Win32",
    webgl_vendor="Intel Inc.",
    renderer="Intel Iris OpenGL Engine",
    fix_hairline=True,
)

# =====================================
# BASE URL
# =====================================

base_url = "https://www.otomoto.pl/osobowe?search%5Bfilter_enum_damaged%5D=0&search%5Badvanced_search_expanded%5D=true"

def wait_for_page_load(driver, timeout=6):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-id]"))
    )

# =====================================
# FUNCTION TO DETECT HTML SELECTORS
# =====================================

def detect_selectors(url):
    """ Detects current HTML selectors for Otomoto listings """
    # Set a random User-Agent before loading the page
    ua = rotate_user_agent()
    try:
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})
    except Exception as e:
        print(f"[!] Error setting User-Agent: {e}")

    driver.get(url)
    time.sleep(random.uniform(5, 10))  # Delay for safety
    page_source = driver.page_source

    # Save HTML to a file for debugging
    with open("otomoto_sample.html", "w", encoding="utf-8") as f:
        f.write(page_source)

    soup = BeautifulSoup(page_source, "html.parser")
    first_offer = soup.find("article", {"data-id": True})
    if not first_offer:
        print("❌ No listings found on the page! Check the file `otomoto_sample.html`")
        return {}

    selectors = {}
    selectors["listing_id"] = "article[data-id]"

    title_tag = first_offer.find("h2")
    if title_tag and title_tag.find("a"):
        selectors["title"] = "h2 a"
        selectors["link"] = "h2 a"

    price_tag = first_offer.find("h3")
    if price_tag:
        selectors["price"] = "h3"

    selectors["currency"] = "p"

    description_tag = first_offer.find("p")
    if description_tag:
        selectors["description"] = "p"

    for param in ["mileage", "fuel_type", "gearbox", "year"]:
        param_tag = first_offer.find("dd", {"data-parameter": param})
        if param_tag:
            selectors[param] = f"dd[data-parameter='{param}']"

    location_tag = first_offer.select_one("dl p")
    if location_tag:
        selectors["location"] = "dl p"

    seller_tag = first_offer.select_one("article.ooa-12g3tpj li")
    if seller_tag:
        selectors["seller_type"] = "article.ooa-12g3tpj li"
    else:
        seller_tag = first_offer.select_one("article li")
        if seller_tag:
            selectors["seller_type"] = "article li"

    indicator_tag = first_offer.select_one("p")
    if indicator_tag:
        selectors["otomoto_indicator"] = "p"

    print(f"✅ Detected selectors: {selectors}")
    return selectors

# =====================================
# FUNCTION TO SPLIT THE BASE URL INTO FILTERED URLS
# =====================================

def split_link(url):
    """
    Splits the main URL into smaller URLs using a year filter and, if necessary, a gearbox filter.
    """
    driver.get(url)
    time.sleep(random.uniform(5, 10))
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    total_pages = 0
    pagination_ul = soup.find("ul", class_="ooa-1vdlgt7")
    if pagination_ul:
        page_numbers = [int(li.text.strip()) for li in pagination_ul.find_all("li") if li.text.strip().isdigit()]
        if page_numbers:
            total_pages = max(page_numbers)
    
    if total_pages <= 500:
        return [url]
    
    filtered_urls = []
    min_year = 2000
    max_year = datetime.now().year
    for start_year in range(min_year, max_year + 1, 2):
        end_year = start_year + 1
        new_url = url.replace("osobowe", f"osobowe/od-{start_year}", 1)
        if "search%5Bfilter_float_year%3Ato%5D" not in new_url:
            new_url += f"&search%5Bfilter_float_year%3Ato%5D={end_year}"
        
        driver.get(new_url)
        time.sleep(random.uniform(3, 6))
        soup_new = BeautifulSoup(driver.page_source, "html.parser")
        total_pages_new = 0
        pagination_ul_new = soup_new.find("ul", class_="ooa-1vdlgt7")
        if pagination_ul_new:
            page_numbers_new = [int(li.text.strip()) for li in pagination_ul_new.find_all("li") if li.text.strip().isdigit()]
            if page_numbers_new:
                total_pages_new = max(page_numbers_new)
        
        if total_pages_new <= 500:
            filtered_urls.append(new_url)
        else:
            for gearbox in ["manual", "automatic"]:
                gearbox_url = new_url + f"&search%5Bfilter_enum_gearbox%5D={gearbox}"
                driver.get(gearbox_url)
                time.sleep(random.uniform(3, 6))
                soup_gear = BeautifulSoup(driver.page_source, "html.parser")
                total_pages_gear = 0
                pagination_ul_gear = soup_gear.find("ul", class_="ooa-1vdlgt7")
                if pagination_ul_gear:
                    page_numbers_gear = [int(li.text.strip()) for li in pagination_ul_gear.find_all("li") if li.text.strip().isdigit()]
                    if page_numbers_gear:
                        total_pages_gear = max(page_numbers_gear)
                filtered_urls.append(gearbox_url)
    return filtered_urls

# =====================================
# DETECT SELECTORS BEFORE SCRAPING
# =====================================

selectors = detect_selectors(base_url)
if not selectors:
    print("❌ No selectors detected! Stopping the script.")
    driver.quit()
    exit()

# =====================================
# GET THE LIST OF URLS TO SCRAPE
# =====================================

filtered_links = split_link(base_url)
print(f"✅ Generated {len(filtered_links)} URLs to scrape.")

# =====================================
# SCRAPING PAGES
# =====================================

all_data = []
unique_keys = set()  # Set to store unique offer keys

def get_total_pages(url):
    driver.get(url)
    time.sleep(random.uniform(3, 6))
    soup = BeautifulSoup(driver.page_source, "html.parser")
    pagination = soup.find("ul", class_="ooa-1vdlgt7")
    if pagination:
        pages = [int(li.text.strip()) for li in pagination.find_all("li") if li.text.strip().isdigit()]
        if pages:
            return max(pages)
    return 1

for filtered_link in filtered_links:
    total_pages = get_total_pages(filtered_link)
    MAX_PAGES = 500  # Maximum page limit
    pages_to_scrape = min(total_pages, MAX_PAGES)
    print(f"🔄 For URL {filtered_link}, found {total_pages} pages, scraping {pages_to_scrape} pages.")
    
    # for page in range(1, pages_to_scrape + 1):
    for page in range(1, 3):
        page_url = f"{filtered_link}&page={page}"
        print(f"🔄 Scraping: {page_url}")
        
        # Set a rotated User-Agent before loading the page
        ua = rotate_user_agent(page)
        try:
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})
        except Exception as e:
            print(f"[!] Error setting User-Agent: {e}")
        
        # Attempt to load the page – implement retry if no offers or captcha is detected
        retry_count = 0
        max_retries = 2
        offers = []
        while retry_count < max_retries:
            try:
                driver.get(page_url)
            except Exception as e:
                print(f"[!] Error loading page {page_url}: {e}")
                retry_count += 1
                time.sleep(10)
                continue

            try:
                wait_for_page_load(driver, timeout=6)
            except Exception as e:
                print(f"[!] Timeout loading page {page_url}: {e}")
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            if is_captcha_page(soup):
                print("❗ Captcha detected. Waiting 90 seconds before retrying.")
                time.sleep(90)
                retry_count += 1
                continue
            
            offers = soup.find_all("article", {"data-id": True})
            if not offers:
                print(f"⚠️ No offers found on page {page_url}. Retrying in 15 seconds.")
                time.sleep(15)
                retry_count += 1
                continue
            else:
                break  # Offers found, exit retry loop
        
        if not offers:
            print(f"⚠️ Skipping page {page_url} after {max_retries} unsuccessful attempts.")
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

                currency_element = offer.find("p", string=lambda text: text and ("PLN" in text or "EUR" in text))
                currency = currency_element.text.strip() if currency_element else "N/A"

                description_elements = offer.select("p")
                description = "N/A"
                for p in description_elements:
                    text = p.text.strip()
                    if "cm3" in text or "KM" in text:
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

                indicator_element = offer.find("p", string=lambda text: text and "średniej" in text)
                indicator = indicator_element.text.strip() if indicator_element else "N/A"

                car = {
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
                    "Otomoto Indicator": indicator,
                    "Scraping Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                # Check for duplicates
                unique_key = create_unique_key(car)
                if unique_key not in unique_keys:
                    all_data.append(car)
                    unique_keys.add(unique_key)
                else:
                    print("🔄 Duplicate offer - skipping.")
            except Exception as e:
                print(f"Error processing offer: {e}")

# =====================================
# SAVE TO CSV
# =====================================

if all_data:
    df = pd.DataFrame(all_data)
    output_dir = "data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    df.to_csv(os.path.join(output_dir, "otomoto_test_ai_agent.csv"), index=False)
    print("✅ Scraping complete! Data saved to otomoto_test_ai_agent.csv")
else:
    print("❌ No data to save. Check the file `otomoto_sample.html`.")

# =====================================
# CLOSE THE BROWSER WITHOUT ERRORS
# =====================================

try:
    driver.quit()
    time.sleep(2)  # Allow time for complete shutdown
except Exception as e:
    print(f"⚠️ Error closing Selenium: {e}")
finally:
    for proc in psutil.process_iter():
        if "chrome" in proc.name().lower():
            try:
                proc.kill()  # Force kill Chrome process if still running
            except psutil.NoSuchProcess:
                pass

print("✅ Script completed successfully!")