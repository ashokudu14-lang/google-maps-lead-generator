import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
try:
    from selenium.webdriver.chrome.service import Service
except ImportError:
    Service = None
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "leads_output.xlsx")

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    # Remove the line below if you want to SEE the browser working (good for demos)
    # options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver

def scrape_google_maps(search_query, max_results=20):
    print(f"Searching for: {search_query}")
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)  # increased from 10 to 20 seconds

    driver.get("https://www.google.com/maps")
    time.sleep(4)  # increased from 2 to 4 seconds

    # Dismiss any consent/cookie popup if it appears
    try:
        consent_button = driver.find_element(By.XPATH, '//button[contains(., "Accept") or contains(., "Agree") or contains(., "I agree")]')
        consent_button.click()
        print("Dismissed consent popup")
        time.sleep(2)
    except:
        pass  # No popup, continue normally

    # Try multiple ways to find the search box
    try:
        search_box = wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
    except:
        try:
            search_box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
        except:
            print("Could not find search box. Taking screenshot for diagnosis...")
            driver.save_screenshot(os.path.join(SCRIPT_DIR, "debug_screenshot.png"))
            driver.quit()
            return []

    search_box.clear()
    search_box.send_keys(search_query)
    search_box.send_keys(Keys.ENTER)
    time.sleep(3)
    

    leads = []
    seen = set()

    print("Scrolling and collecting results...")

    while len(leads) < max_results:
        # Find all result cards currently loaded
        results = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")

        for result in results:
            if len(leads) >= max_results:
                break

            try:
                # Get name
                name = result.find_element(By.CSS_SELECTOR, "div.qBF1Pd").text.strip()
                if name in seen:
                    continue
                seen.add(name)

                # Click on result to open details panel
                result.click()
                time.sleep(2)

                # Extract details from side panel
                rating = ""
                address = ""
                phone = ""
                website = ""

                try:
                    rating = driver.find_element(By.CSS_SELECTOR, "div.F7nice span").text.strip()
                except:
                    pass

                try:
                    address = driver.find_element(
                        By.CSS_SELECTOR, "button[data-item-id='address'] div.Io6YTe"
                    ).text.strip()
                except:
                    pass

                try:
                    phone = driver.find_element(
                        By.CSS_SELECTOR, "button[data-item-id^='phone'] div.Io6YTe"
                    ).text.strip()
                except:
                    pass

                try:
                    website = driver.find_element(
                        By.CSS_SELECTOR, "a[data-item-id='authority'] div.Io6YTe"
                    ).text.strip()
                except:
                    pass

                leads.append({
                    "Business Name": name,
                    "Rating": rating,
                    "Address": address,
                    "Phone": phone,
                    "Website": website,
                })

                print(f"Collected ({len(leads)}): {name}")

            except Exception as e:
                continue

        # Scroll down the results list to load more
        try:
            scrollable = driver.find_element(By.CSS_SELECTOR, "div[role='feed']")
            driver.execute_script("arguments[0].scrollTop += 1000", scrollable)
            time.sleep(2)
        except:
            break

    driver.quit()
    return leads

def save_to_excel(leads, output_file):
    df = pd.DataFrame(leads)
    df.to_excel(output_file, index=False)
    print(f"\nSaved {len(df)} leads to {output_file}")

if __name__ == "__main__":
    query = input("Enter search (e.g. 'dentists in Hyderabad'): ").strip()
    max_r = input("How many results? (default 20): ").strip()
    max_r = int(max_r) if max_r.isdigit() else 20

    leads = scrape_google_maps(query, max_results=max_r)

    if leads:
        save_to_excel(leads, OUTPUT_FILE)
    else:
        print("No leads found. Try a different search.")
        