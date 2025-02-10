import os
import time
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup

# List of sample User-Agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0_1) AppleWebKit/535.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/535.36",
]

def rotate_user_agent(index=None):
    """
    Returns a User-Agent from the list.
    - If 'index' is provided, it returns one based on the index (cycling through the list).
    - Otherwise, it returns a random User-Agent.
    """
    if index is not None:
        return USER_AGENTS[index % len(USER_AGENTS)]
    else:
        return random.choice(USER_AGENTS)

def is_captcha_page(soup):
    """
    Checks if the page contains text indicating a "Too many requests" or "captcha" message.
    If found, it suggests that the scraper has been blocked.
    """
    text = soup.get_text().lower()
    if "zbyt wiele zapytań" in text or "captcha" in text:
        return True
    return False

def create_unique_key(car):
    """
    Creates a unique key for a car entry based on a combination of fields:
    (Title, Description, Mileage, Fuel Type, Gearbox, Year, Location, Seller Type, Price).
    This key helps in filtering out duplicate records.
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
    # Clean up spaces and join into a single string using a delimiter
    fields = [str(x).strip() for x in fields]
    return "|".join(fields)

def scrape_page(url, session=None, user_agent=None):
    """
    Fetches and parses a single page of listings.
    Returns a tuple: (list_of_car_offers, final_url)
       - list_of_car_offers -> list of dictionaries containing car data
       - final_url -> the actual URL after any potential redirection
    """
    if session is None:
        session = requests

    # Prepare HTTP headers with the User-Agent and language preference
    headers = {
        'User-Agent': user_agent if user_agent else random.choice(USER_AGENTS),
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    # Execute the HTTP GET request
    try:
        resp = session.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"[!] Error during request {url}: {e}")
        return [], url  # Assume the URL did not change in case of an error

    final_url = resp.url  # This may be useful if the server performs a redirect

    # Handle HTTP errors
    if resp.status_code == 404:
        print(f"[!] 404 Page not found: {url}")
        return [], final_url
    if resp.status_code >= 400:
        print(f"[!] HTTP error {resp.status_code} while fetching {url}")
        return [], final_url

    # Parse the page content with BeautifulSoup
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Check for anti-bot measures like CAPTCHA
    if is_captcha_page(soup):
        print("[!] CAPTCHA or block detected - taking a longer break (90s).")
        time.sleep(90)
        return [], final_url

    # Find all listing articles on the page (updated selector for current HTML version)
    listings = soup.find_all('article', {'class': 'ooa-1yux8sr e1wxlbcc0'})
    cars = []

    if not listings:
        snippet = resp.text[:1000]  # Grab a snippet of HTML for debugging
        print("[!] No listings found on the page. HTML snippet:", snippet)
        return [], final_url

    # Process each listing found on the page
    for listing in listings:
        try:
            # Extract title and link
            title_element = listing.select_one('h2.e1n1d04s0 a')
            title = title_element.text.strip() if title_element else 'N/A'
            link = title_element['href'] if title_element else 'N/A'

            # Extract description
            description_element = listing.select_one('p.ewg8vos8')
            description = description_element.text.strip() if description_element else 'N/A'

            # Extract mileage information
            mileage_element = listing.select_one('dd[data-parameter="mileage"]')
            mileage = mileage_element.text.strip() if mileage_element else 'N/A'

            # Extract fuel type
            fuel_type_element = listing.select_one('dd[data-parameter="fuel_type"]')
            fuel_type = fuel_type_element.text.strip() if fuel_type_element else 'N/A'

            # Extract gearbox information
            gearbox_element = listing.select_one('dd[data-parameter="gearbox"]')
            gearbox = gearbox_element.text.strip() if gearbox_element else 'N/A'

            # Extract year of manufacture
            year_element = listing.select_one('dd[data-parameter="year"]')
            year = year_element.text.strip() if year_element else 'N/A'

            # Extract location (first occurrence of the specific element)
            location_element = listing.select_one('dl.ooa-1o0axny p.ooa-gmxnzj')
            location = location_element.text.strip() if location_element else 'N/A'

            # Extract seller type
            seller_type_element = listing.select_one('article.ooa-12g3tpj li')
            seller_type = seller_type_element.text.strip() if seller_type_element else 'N/A'

            # Extract price
            price_element = listing.select_one('h3.e6r213i1')
            price = price_element.text.strip() if price_element else 'N/A'

            # Extract currency information
            currency_element = listing.select_one('p.e6r213i2')
            currency = currency_element.text.strip() if currency_element else 'N/A'

            # Extract additional indicator (e.g., "Within average range")
            indicator_element = listing.select_one('p.elf9i0b2')
            indicator = indicator_element.text.strip() if indicator_element else 'N/A'

            # Get the listing ID from the data attribute
            listing_id = listing.get('data-id', 'N/A')

            # Build a dictionary for the car's data
            car = {
                'ID': listing_id,
                'Title': title,
                'Link': link,
                'Description': description,
                'Mileage': mileage,
                'Fuel Type': fuel_type,
                'Gearbox': gearbox,
                'Year': year,
                'Location': location,
                'Seller Type': seller_type,
                'Price': price,
                'Currency': currency,
                'Otomoto Indicator': indicator
            }
            cars.append(car)

        except Exception as e:
            print(f"Error parsing listing: {e}")

    return cars, final_url

def scrape_multiple_links(base_urls, output_dir, max_pages=500):
    """
    Main function to scrape multiple base URLs.
    - base_urls: list of starting URLs
    - output_dir: directory where CSV files will be saved
    - max_pages: maximum number of pages to scrape per base URL
    """
    # Ensure that the output directory exists; if not, create it
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    # Initialize a requests session to persist cookies and other settings
    session = requests.Session()

    # Process each base URL one by one
    for idx, base_url in enumerate(base_urls, 1):
        print(f"\n[*] Start scraping from: {base_url}")

        # Define a unique CSV file for this base URL
        output_file = os.path.join(output_dir, f"otomoto_listings_{idx}.csv")

        # Load existing records and build a set of unique keys to avoid duplicates
        all_unique_keys = set()
        if os.path.exists(output_file):
            existing_data = pd.read_csv(output_file)
            print(f"Loaded {len(existing_data)} rows from {output_file}.")

            # Replace missing values with empty strings for consistency
            existing_data.fillna('', inplace=True)
            for _, row in existing_data.iterrows():
                car = {
                    'Title': row.get('Title', ''),
                    'Description': row.get('Description', ''),
                    'Mileage': row.get('Mileage', ''),
                    'Fuel Type': row.get('Fuel Type', ''),
                    'Gearbox': row.get('Gearbox', ''),
                    'Year': row.get('Year', ''),
                    'Location': row.get('Location', ''),
                    'Seller Type': row.get('Seller Type', ''),
                    'Price': row.get('Price', '')
                }
                unique_key = create_unique_key(car)
                all_unique_keys.add(unique_key)

            print(f"Unique records in memory: {len(all_unique_keys)}")
        else:
            print("[!] Output file not found, starting fresh.")

        # Variable to track if the page URL has not changed (indicating a possible redirect loop)
        last_final_url = None
        repeat_url_count = 0

        # Counter for consecutive pages with no new offers
        consecutive_empty_pages = 0

        # Loop through pages up to max_pages
        for page_number in range(1, max_pages + 1):
            page_url = f"{base_url}&page={page_number}"
            print(f"Scraping: {page_url} [page {page_number}/{max_pages}]")

            # Rotate user-agent based on the page number
            user_agent = rotate_user_agent(index=page_number)

            # Scrape the page and retrieve car listings and the final URL
            cars, final_url = scrape_page(page_url, session=session, user_agent=user_agent)

            # Check if the final URL is the same as the previous one
            if final_url == last_final_url:
                repeat_url_count += 1
                print(f"  -> final_url did not change, repeat count: {repeat_url_count}.")
            else:
                repeat_url_count = 0
                last_final_url = final_url

            # If the same final URL appears twice consecutively, break out of the loop
            if repeat_url_count >= 2:
                print("[!] The same page was reached twice. Moving to the next base URL.")
                break

            # If no car listings are found on the page
            if not cars:
                if consecutive_empty_pages == 0:
                    # Try a short retry if it's the first empty page
                    consecutive_empty_pages += 1
                    print("[!] Empty page – retrying after a short break (15s).")
                    time.sleep(15)
                    continue
                else:
                    # If two empty pages in a row, stop scraping this base URL
                    print(f"[!] No more cars found at page {page_number}. Moving to next URL.")
                    break

            # Check for uniqueness of each car listing using the unique key
            new_cars = []
            for car in cars:
                unique_key = create_unique_key(car)
                if unique_key not in all_unique_keys:
                    new_cars.append(car)
                    all_unique_keys.add(unique_key)

            # If there are new unique records, append them to the CSV file
            if new_cars:
                new_df = pd.DataFrame(new_cars)
                if os.path.exists(output_file):
                    new_df.to_csv(output_file, mode='a', header=False, index=False)
                else:
                    new_df.to_csv(output_file, index=False)

                print(f"  -> Added {len(new_cars)} new records. Total unique records: {len(all_unique_keys)}")
                consecutive_empty_pages = 0  # Reset the empty pages counter since we found new offers
            else:
                consecutive_empty_pages += 1
                print(f"  -> No new unique records on this page (streak={consecutive_empty_pages}).")
                if consecutive_empty_pages >= 3:
                    print("[!] Three consecutive pages without new offers. Moving to the next base URL.")
                    break

            # Wait for a random short period to reduce the risk of being blocked
            sleep_time = random.uniform(3, 5)
            print(f"Sleeping {sleep_time:.1f} sec...")
            time.sleep(sleep_time)

        print(f"Done with base URL: {base_url}")

    print("All base URLs have been processed.")

if __name__ == "__main__":
    # List of base URLs to scrape (you only need to define them once here)
    base_urls = [
        'https://www.otomoto.pl/osobowe/abarth--acura--aiways--aixam--alfa-romeo--alpina--alpine--arcfox--asia--aston-martin--austin--autobianchi--avatr--baic--bentley--brilliance--bugatti--buick--byd--cadillac--casalini--caterham--cenntro--changan--chatenet--chevrolet--chrysler--citroen--cupra?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/audi?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_gearbox%5D=automatic&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/audi?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_gearbox%5D=manual&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/bmw?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_fuel_type%5D%5B0%5D=petrol-cng&search%5Bfilter_enum_fuel_type%5D%5B1%5D=petrol-lpg&search%5Bfilter_enum_fuel_type%5D%5B2%5D=diesel&search%5Bfilter_enum_fuel_type%5D%5B3%5D=electric&search%5Bfilter_enum_fuel_type%5D%5B4%5D=etanol&search%5Bfilter_enum_fuel_type%5D%5B5%5D=hybrid&search%5Bfilter_enum_fuel_type%5D%5B6%5D=plugin-hybrid&search%5Bfilter_enum_fuel_type%5D%5B7%5D=hidrogen&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/bmw?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_fuel_type%5D=petrol&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/dacia--daewoo--daihatsu--delorean--dfm--dfsk--dkw--dodge--doosan--dr-motor--ds-automobiles--e-go--elaris--faw--fendt--ferrari--fiat--fisker?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/ford?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_gearbox%5D=manual&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/ford?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_gearbox%5D=automatic&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/forthing--gaz--geely--genesis--gmc--gwm--hiphi--honda--hongqi--hummer--hyundai--iamelectric--ineos--infiniti--isuzu--iveco--jac--jaecoo--jaguar--inny?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/jeep--jetour--jinpeng--kia--ktm--lada--lamborghini--lancia--land-rover--leapmotor--levc?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/lexus--ligier--lincoln--lixiang--lotus--lti--lucid--lynk-and-co--man--maserati--maximus--maxus--maybach--mazda--mclaren--mercury--mg--microcar--mini--mitsubishi--morgan--nio?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/mercedes-benz?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_gearbox%5D=automatic&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/mercedes-benz?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_gearbox%5D=manual&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/nissan--nysa--oldsmobile--omoda--piaggio--plymouth--polestar--polonez--pontiac--porsche--ram?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/opel?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_gearbox%5D=automatic&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/opel?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_gearbox%5D=manual&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/peugeot?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/renault--rolls-royce--rover--saab--sarini--saturn?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/seat--seres--shuanghuan--skywell--skyworth--smart--ssangyong--subaru--suzuki--syrena--tarpan--tata--tesla?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/skoda?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/toyota?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/trabant--triumph--uaz--vauxhall--velex--volvo--voyah--waltra--marka_warszawa--wartburg--wolga--xiaomi--xpeng--zaporozec--zastawa--zeekr--zhidou--zuk?search%5Bfilter_enum_damaged%5D=0&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/volkswagen?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_gearbox%5D=manual&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true',
        'https://www.otomoto.pl/osobowe/volkswagen?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_gearbox%5D=automatic&search%5Border%5D=relevance_web&search%5Badvanced_search_expanded%5D=true'
    ]

    # Directory where CSV files will be saved
    output_dir = "data/otomoto_listings"

    # Maximum number of pages to scrape per base URL
    max_pages = 500

    scrape_multiple_links(base_urls, output_dir, max_pages)