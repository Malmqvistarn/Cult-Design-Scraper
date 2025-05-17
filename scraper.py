from __future__ import annotations

import os
import time
import io
import requests
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# === CONFIGURATION ===
LISTING_URL             = "https://hedlundgruppen.gung.io/categories/sAllaProdukterCult?limit=288"
PRODUCT_URL_TEMPLATE    = "https://hedlundgruppen.gung.io/product/{sku}"
OUTPUT_DIR              = "output"
HEADLESS                = False
SCROLL_PAUSE_SECONDS    = 0.5
MANUAL_LOGIN_WAIT       = 10
# ======================

def create_webdriver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)

def scroll_to_load_all(driver: webdriver.Chrome) -> None:
    """Scrolls to the bottom repeatedly until no new content loads."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_SECONDS)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def convert_to_webp(image_bytes: bytes, output_path: str) -> None:
    """Converts raw image bytes to optimized WEBP and saves to disk."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Ensure correct mode for conversion
        if img.mode in ("RGBA", "LA"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        img.save(output_path, format="WEBP", optimize=True)

def scrape_products():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = create_webdriver()
    try:
        # 1) Open the listing page and allow manual login
        driver.get(LISTING_URL)
        print(f"Opened listing page. Waiting {MANUAL_LOGIN_WAIT}s for manual login...")
        time.sleep(MANUAL_LOGIN_WAIT)

        # 2) Scroll through the listing to load all products, then collect SKUs
        scroll_to_load_all(driver)
        product_cards = driver.find_elements(By.CSS_SELECTOR, "div.card.product-card")
        skus = [card.find_element(By.CSS_SELECTOR, "small span").text.strip() for card in product_cards]
        total = len(skus)
        print(f"Found {total} products via SKUs.")

        # 3) Iterate over each SKU and scrape its page
        for index, sku in enumerate(skus, start=1):
            product_url = PRODUCT_URL_TEMPLATE.format(sku=sku)
            driver.get(product_url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-name"))
            )

            # --- Extract product metadata ---
            title = driver.find_element(By.CSS_SELECTOR, "h1.product-name").text.strip()

            # Description (using find_elements to avoid exceptions)
            desc_elements = driver.find_elements(By.CSS_SELECTOR, ".product-description")
            description = desc_elements[0].text.strip() if desc_elements else ""
            if not description:
                print(f"⚠️ No description found for SKU {sku}")

            # Price and stock status
            price_text = driver.find_element(By.CSS_SELECTOR, "lib-price-inside span span").text.strip()
            price = price_text.split()[0]
            availability_text = driver.find_element(By.CSS_SELECTOR, "lib-availability a").text.lower()
            in_stock = "YES" if "lager" in availability_text else "NO"

            # Optional extra attributes from the attribute table
            extra_attributes: dict[str, str] = {}
            try:
                table = driver.find_element(By.CSS_SELECTOR, ".attribute-table")
                for row in table.find_elements(By.TAG_NAME, "tr"):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) == 2:
                        label = cells[0].text.strip().rstrip(":")
                        value = cells[1].text.strip()
                        extra_attributes[label] = value
            except NoSuchElementException:
                pass

            # --- Gather high-res image URLs ---
            image_urls: list[str] = []
            # Main image
            try:
                main_img = driver.find_element(By.CSS_SELECTOR, ".image-container img")
                image_urls.append(main_img.get_attribute("src"))
            except NoSuchElementException:
                print(f"⚠️ No main image found for SKU {sku}")

            # Thumbnails: click each to load its high-res version
            thumbnails = driver.find_elements(By.CSS_SELECTOR, ".product-detail-image img")
            if not thumbnails:
                print(f"⚠️ No thumbnails found for SKU {sku}")
            for thumb in thumbnails:
                try:
                    driver.execute_script("arguments[0].click();", thumb)
                    time.sleep(0.2)
                    current_main = driver.find_element(By.CSS_SELECTOR, ".image-container img")
                    src = current_main.get_attribute("src")
                    if src not in image_urls:
                        image_urls.append(src)
                except Exception as e:
                    print(f"⚠️ Failed to click thumbnail for SKU {sku}: {e}")

            if not image_urls:
                print(f"⚠️ No image URLs collected for SKU {sku}")

            # --- Download and convert images to WEBP ---
            product_dir = os.path.join(OUTPUT_DIR, sku)
            os.makedirs(product_dir, exist_ok=True)
            for idx, img_url in enumerate(image_urls, start=1):
                try:
                    response = requests.get(img_url, timeout=30)
                    response.raise_for_status()
                    webp_path = os.path.join(product_dir, f"{idx}.webp")
                    convert_to_webp(response.content, webp_path)
                except Exception as e:
                    print(f"⚠️ Could not download/convert image {img_url} for SKU {sku}: {e}")

            # --- Save metadata to a text file ---
            metadata_lines = [
                f"SKU: {sku}",
                f"Title: {title}",
                f"Price: {price}",
                f"In stock: {in_stock}",
                "",
                description
            ]
            for label, val in extra_attributes.items():
                metadata_lines.append(f"{label}: {val}")

            meta_file = os.path.join(product_dir, "data.txt")
            with open(meta_file, "w", encoding="utf-8") as f:
                f.write("\n".join(metadata_lines))

            print(f"[{index}/{total}] ✅ SKU {sku} saved with {len(image_urls)} WEBP images")

    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_products()
