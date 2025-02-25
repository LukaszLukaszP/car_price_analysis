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
options.add_argument("--disable-blink-features=AutomationControlled")  # ✅ Hides Selenium usage
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

# 📌 INITIALIZING SELENIUM
service = Service("C:/WINDOWS/system32/chromedriver.exe")  # Ensure that the path is correct
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

def wait_for_page_load(driver, timeout=6):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-id]"))
    )

# 📌 FUNCTION TO DETECT HTML SELECTORS
def detect_selectors(url):
    """Detects current HTML selectors for Otomoto listings."""
    driver.get(url)
    time.sleep(random.uniform(5, 10))  # ✅ Delay for safety
    page_source = driver.page_source

    # 📌 Save HTML to a file for debugging
    with open("otomoto_sample.html", "w", encoding="utf-8") as f:
        f.write(page_source)

    soup = BeautifulSoup(page_source, "html.parser")

    # 🔍 Search for the first listing
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

# 📌 FUNCTION TO SPLIT LINKS USING FILTERS SO THAT THE NUMBER OF PAGES DOES NOT EXCEED 500
def split_link(url):
    """
    Splits the main URL into smaller URLs by applying a year filter and, if necessary, a gearbox filter.
    Example filtered URLs:
      - Year 2000-2001 + manual gearbox:
        https://www.otomoto.pl/osobowe/od-2000?search%5Bfilter_enum_damaged%5D=0&search%5Badvanced_search_expanded%5D=true&search%5Bfilter_float_year%3Ato%5D=2001&search%5Bfilter_enum_gearbox%5D=manual
      - Year 2000-2001 + automatic gearbox:
        https://www.otomoto.pl/osobowe/od-2000?search%5Bfilter_enum_damaged%5D=0&search%5Badvanced_search_expanded%5D=true&search%5Bfilter_float_year%3Ato%5D=2001&search%5Bfilter_enum_gearbox%5D=automatic
    """
    # Load the page and get the number of pages
    driver.get(url)
    time.sleep(random.uniform(5, 10))
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    total_pages = 0
    pagination_ul = soup.find("ul", class_="ooa-1vdlgt7")
    if pagination_ul:
        page_numbers = [int(li.text.strip()) for li in pagination_ul.find_all("li") if li.text.strip().isdigit()]
        if page_numbers:
            total_pages = max(page_numbers)
    
    # If the number of pages is less than or equal to 500, do not split the URL
    if total_pages <= 500:
        return [url]
    
    filtered_urls = []
    # Define the range of years, for example from 2000 to 2023
    min_year = 2000
    max_year = 2023
    # Iterate through two-year intervals
    for start_year in range(min_year, max_year + 1, 2):
        end_year = start_year + 1
        # Modify the URL by adding a year filter
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
        
        # If the number of pages after applying the year filter is less than or equal to 500, add the URL
        if total_pages_new <= 500:
            filtered_urls.append(new_url)
        else:
            # If there are still too many pages, split further by gearbox type
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

# 📌 DETECT HTML SELECTORS BEFORE SCRAPING
selectors = detect_selectors(base_url)
if not selectors:
    print("❌ Selectors not detected! Stopping the script.")
    driver.quit()
    exit()

# 📌 OBTAINING THE LIST OF URLS TO SCRAPE (splitting the URL if the number of pages > 500)
filtered_links = split_link(base_url)
print(f"✅ Generated {len(filtered_links)} links for scraping.")

# 📌 SCRAPING PAGES
all_data = []

# Function to get the total number of pages from pagination for a given URL
def get_total_pages(url):
    driver.get(url)
    time.sleep(random.uniform(3, 6))
    soup = BeautifulSoup(driver.page_source, "html.parser")
    pagination = soup.find("ul", class_="ooa-1vdlgt7")
    if pagination:
        # Retrieve all 'li' elements containing page numbers
        pages = [int(li.text.strip()) for li in pagination.find_all("li") if li.text.strip().isdigit()]
        if pages:
            return max(pages)
    return 1  # Default to 1 page if unable to retrieve the number

# Iterate over each filtered URL
for filtered_link in filtered_links:
    total_pages = get_total_pages(filtered_link)
    MAX_PAGES = 500  # Maximum page limit (as a safeguard)
    pages_to_scrape = min(total_pages, MAX_PAGES)
    print(f"🔄 For URL {filtered_link}, found {total_pages} pages, scraping {pages_to_scrape} pages.")
    
    for page in range(1, pages_to_scrape + 1):
        page_url = f"{filtered_link}&page={page}"
        print(f"🔄 Scraping: {page_url}")

        driver.get(page_url)
        wait_for_page_load(driver, timeout=6)

        # 📌 Retrieve HTML and parse it
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        offers = soup.find_all("article", {"data-id": True})

        if not offers:
            print(f"⚠️ No listings found on page {page_url}. Check `otomoto_page_{page}.html`.")
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

                description_element = offer.select("p")  # Retrieves all 'p' elements
                description = "N/A"

                for p in description_element:
                    text = p.text.strip()
                    if "cm3" in text or "KM" in text:  # Check if the text looks like a technical description
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

                indicator_element = offer.find("p", string=lambda text: text and "średniej" in text)  # Look for text indicating average price
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

# 📌 GRACEFULLY CLOSING THE BROWSER
try:
    driver.quit()
    time.sleep(2)  # ✅ Allow time for the process to fully terminate
except Exception as e:
    print(f"⚠️ Problem closing Selenium: {e}")
finally:
    for proc in psutil.process_iter():
        if "chrome" in proc.name().lower():
            try:
                proc.kill()  # ✅ Forcefully terminate the Chrome process if still running
            except psutil.NoSuchProcess:
                pass

print("✅ Script finished successfully!")
