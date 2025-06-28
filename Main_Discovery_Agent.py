import time
import re
import datetime
import sqlite3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

# --- CONFIGURATION SECTION ---
chromedriver_path = 'chromedriver.exe'
db_file = 'credit_card_data.db'
bank_listing_urls = {
    "Mashreq Bank": "https://www.mashreq.com/en/uae/neo/cards/",
    "ADCB": "https://www.adcb.com/en/personal/cards/credit-cards/",
    "RAKBANK": "https://www.rakbank.ae/en",
    "Emirates NBD": "https://www.emiratesnbd.com/en/cards/credit-cards/",
    "FAB (First Abu Dhabi Bank)": "https://www.bankfab.com/en-ae/personal/credit-cards",
    "HSBC": "https://www.hsbc.ae/credit-cards/products/",
    "DIB": "https://www.dib.ae/personal/cards/?cardType=All-Cards&income=Any&cardBenefit=All-Benefits&visible=24"
}

# --- DATABASE SETUP ---
def setup_database():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_inventory (
            id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL, bank_name TEXT,
            first_discovered_date TEXT, last_verified_date TEXT, is_active BOOLEAN
        );
    ''')
    conn.commit()
    conn.close()
    print(f"Database '{db_file}' is ready.\n")

# --- HELPER & DISCOVERY FUNCTIONS from _4.py ---
def get_links_from_soup_for_bank(soup_obj, base_listing_url, bank_name):
    found_links_raw = []
    EXCLUSION_PATTERNS = [
        r'(apply|faq|terms|fees|login|calculator|disclaimer|promotions)', r'offers/', r'services/', 
        r'compare/', r'rewards/', r'how-to-pop-up', r'ar/', r'sitecore/', r'campaigns/', 
        r'contact-us/', r'overview/', r'salary-prepay-card', r'contactless-payments', 
        r'credit-shield-pro', r'vox-credit-card-movie-benefits', r'pay-your-credit-card-dues-in-installments', 
        r'manage-your-credit-card-limits', r'business-banking#', r'priority-banking', 
        r'application\.emiratesnbd\.com', r'cards/?$', r'accounts/', r'digital/', r'solutions/', 
        r'about-us/', r'commercial-cards/', r'business-cards/', r'sitemap\.xml', r'prepaid-cards/'
    ]
    exclude_regex = re.compile('|'.join(EXCLUSION_PATTERNS), re.IGNORECASE)

    if bank_name == "Mashreq Bank":
        # Note: The class from your file 'ProductCardTop_imageContainer__xrlQX' may be outdated.
        # Our recent tests found 'card-item_card-item__' to be more reliable.
        # Let's try a more general approach that might catch either.
        elements = soup_obj.find_all('a', href=True)
        for el in elements:
            if '/cards/credit-cards/' in el.get('href', ''):
                 found_links_raw.append(el.get('href'))
    # ... (Other bank-specific logic from your file would go here) ...
    # For now, focusing on a general fallback that might work for Mashreq.
    if not found_links_raw:
        general_card_url_regex = re.compile(r'(credit-card|cards|card-details)', re.IGNORECASE)
        all_links = soup_obj.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            if href and general_card_url_regex.search(href):
                found_links_raw.append(href)

    filtered_links_raw = [link for link in found_links_raw if not exclude_regex.search(link)]
    absolute_unique_urls = set()
    for rel_url in filtered_links_raw:
        absolute_unique_urls.add(urljoin(base_listing_url, rel_url.rstrip('/')))
    return list(absolute_unique_urls)

def discover_and_store_urls(bank_name, listing_url):
    print(f"--- Discovering cards for {bank_name} ---")
    driver = None
    try:
        service = Service(executable_path=chromedriver_path)
        options = webdriver.ChromeOptions()
        # Using visible mode as it proved more stable in our tests
        # options.add_argument('--headless') 
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(listing_url)
        print("  Waiting 10 seconds for page to load...")
        time.sleep(10)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        found_card_urls = get_links_from_soup_for_bank(soup, listing_url, bank_name)
        
        if found_card_urls:
            print(f"  Found {len(found_card_urls)} unique card links.")
            # --- Store in Database ---
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for url in found_card_urls:
                cursor.execute("""
                    INSERT INTO card_inventory (url, bank_name, first_discovered_date, last_verified_date, is_active)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (url) DO UPDATE SET last_verified_date = excluded.last_verified_date, is_active = 1;
                """, (url, bank_name, current_datetime, current_datetime, 1))
            conn.commit()
            conn.close()
            print(f"  Database updated for {bank_name}.")
        else:
            print(f"  No unique card links found for {bank_name}.")

    except Exception as e:
        print(f"  An error occurred during discovery for {bank_name}: {e}")
    finally:
        if driver:
            print("  Closing browser...")
            driver.quit()

# --- MAIN EXECUTION LOOP ---
if __name__ == "__main__":
    setup_database()
    for bank_name, url in bank_listing_urls.items():
        discover_and_store_urls(bank_name, url)
        if len(bank_listing_urls) > 1:
            print("\nPausing for 15 seconds before next bank...\n")
            time.sleep(15)
    print("\n--- Main Discovery Agent run has finished. ---")