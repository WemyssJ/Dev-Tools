# -*- coding: utf-8 -*-
"""
generate_sharepoint_links_selenium.py
──────────────────────────────────────
Uses Selenium to navigate to the SharePoint drone photos folder,
generate an "Anyone with the link" share link for each file, and
patch the CSV.

Requirements:
    py -m pip install selenium webdriver-manager

Usage:
    py generate_sharepoint_links_selenium.py

If Sharepoint doesn't load, run this:
rmdir /s /q "C:\Users\wemyssj\AppData\Local\Temp\selenium_chrome"
taskkill /f /im chrome.exe

"""

import csv
import json
import os
import re
import sys
import time

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    sys.exit("Run:  py -m pip install selenium webdriver-manager")

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

CSV_PATH = r"C:\Users\wemyssj\Craddys\CraddysDrones - 13914 - Plots 2 - 3, Silverthorne Lane\20260318 Drone Canal Wall Photos\OSGridExtraction.csv"

PLACEHOLDER = "PUBLIC_LINK_FOR_"

SHAREPOINT_FOLDER_URL = (
    "https://craddysuk.sharepoint.com/sites/CraddysDrones/CraddysDrones%20Files"
    "/Forms/AllItems.aspx?id=%2Fsites%2FCraddysDrones%2FCraddysDrones%20Files"
    "%2F13914%20%2D%20Plots%202%20%2D%203%2C%20Silverthorne%20Lane"
    "%2F20260318%20Drone%20Canal%20Wall%20Photos"
)

WAIT_TIMEOUT = 30

# ──────────────────────────────────────────────


def get_filenames_needing_links(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader  = csv.DictReader(f)
        rows    = list(reader)
        headers = reader.fieldnames

    targets = []
    for i, row in enumerate(rows):
        current = row.get("Public Sharepoint Link", "").strip()
        fname   = row.get("File", "").strip()
        if fname and (not current or current.startswith(PLACEHOLDER)):
            targets.append((i, fname))

    return rows, headers, targets


def patch_csv(csv_path, rows, headers, results):
    for row_index, url in results.items():
        rows[row_index]["Public Sharepoint Link"] = url
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def extract_url_from_iframe(driver):
    """
    Extract the sharing URL from the g_sharingInformation JS object
    that SharePoint embeds in the iframe page source.
    This is far more reliable than scraping an input element.

    We click 'Copy link' first to make SharePoint generate the anonymous
    link, then read the URL from the updated JS object or from the
    clipboard via JS.
    """
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    # ── Click "Copy link" button (aria-label='Copy link') ─────────────
    try:
        copy_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[@aria-label='Copy link']"
        )))
        driver.execute_script("arguments[0].click();", copy_btn)
        time.sleep(2)  # Wait for SharePoint to generate & copy the link
    except TimeoutException:
        return None, "Could not find 'Copy link' button"

    # ── Method 1: read from clipboard via JS ──────────────────────────
    url = None
    try:
        url = driver.execute_script(
            "return await navigator.clipboard.readText();"
        )
        if url and url.startswith("http"):
            return url, None
    except Exception:
        pass

    # ── Method 2: extract from g_sharingInformation in page source ────
    try:
        page_source = driver.page_source
        # Look for the sharing link in the JS payload
        # SharePoint embeds anonymous links as "url":"https://..." after Copy
        matches = re.findall(r'"url"\s*:\s*"(https://[^"]+sharepoint[^"]+)"', page_source)
        if matches:
            # Prefer the shortest URL (the share link, not the directUrl)
            url = min(matches, key=len)
            return url, None

        # Also try directUrl as fallback (this is the direct file link)
        match = re.search(r'"directUrl"\s*:\s*"(https://[^"]+)"', page_source)
        if match:
            url = match.group(1).replace("\\u0026", "&")
            return url, None
    except Exception:
        pass

    # ── Method 3: look for any input with a sharepoint URL ────────────
    try:
        inputs = driver.find_elements(By.XPATH, "//input")
        for inp in inputs:
            val = inp.get_attribute("value") or ""
            if val.startswith("http") and "sharepoint" in val:
                return val, None
    except Exception:
        pass

    return None, "Could not extract URL from share dialog"


def get_share_link_for_file(driver, filename):
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    # Ensure we're on the main page
    driver.switch_to.default_content()

    # ── Find the file row ──────────────────────────────────────────────
    try:
        file_el = wait.until(EC.presence_of_element_located((
            By.XPATH,
            f"//span[normalize-space(text())='{filename}'] | //a[normalize-space(@title)='{filename}']"
        )))
    except TimeoutException:
        return None, f"Could not find '{filename}' in the file list"

    # ── Hover to reveal the row action buttons ─────────────────────────
    ActionChains(driver).move_to_element(file_el).perform()
    time.sleep(0.4)

    # ── Click the '...' (more actions) button ─────────────────────────
    try:
        row_el = file_el.find_element(By.XPATH,
            "ancestor::div[contains(@class,'ms-DetailsRow') or contains(@class,'listItem')][1]"
        )
        more_btn = row_el.find_element(By.XPATH,
            ".//button[@aria-label='More actions' or @title='More actions' "
            "or @data-automationid='FieldRenderer-name--More']"
        )
        more_btn.click()
    except NoSuchElementException:
        ActionChains(driver).context_click(file_el).perform()

    time.sleep(0.5)

    # ── Click "Share" in the context menu ─────────────────────────────
    try:
        share_item = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//span[normalize-space(text())='Share'] "
            "| //button[normalize-space(text())='Share'] "
            "| //li[normalize-space(.)='Share']"
        )))
        share_item.click()
    except TimeoutException:
        driver.find_element(By.TAG_NAME, "body").click()
        return None, f"Share menu item not found for '{filename}'"

    time.sleep(0.5)

    # ── Switch INTO the share iframe ───────────────────────────────────
    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "shareFrame"))
        )
    except TimeoutException:
        driver.switch_to.default_content()
        return None, f"Share iframe did not appear for '{filename}'"

    # Wait for iframe content to fully load
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Copy link']"))
    )

    # ── Extract URL and click Copy ─────────────────────────────────────
    url, err = extract_url_from_iframe(driver)

    # ── Switch back and close dialog ──────────────────────────────────
    driver.switch_to.default_content()
    _close_dialog(driver)

    if url and url.startswith("http"):
        return url, None
    return None, err or f"Could not read link for '{filename}'"


def _close_dialog(driver):
    driver.switch_to.default_content()
    try:
        close_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((
            By.XPATH,
            "//button[@aria-label='Close' or @title='Close' "
            "or contains(@class,'closeButton') "
            "or contains(@class,'ms-Dialog-button--close')]"
        )))
        driver.execute_script("arguments[0].click();", close_btn)
        time.sleep(0.4)
    except Exception:
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys("\x1b")
            time.sleep(0.3)
        except Exception:
            pass


def main():
    rows, headers, targets = get_filenames_needing_links(CSV_PATH)

    if not targets:
        print("All rows already have links. Nothing to do.")
        return

    print(f"Found {len(targets)} file(s) needing links.\n")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(r"--user-data-dir=C:\Users\wemyssj\AppData\Local\Temp\selenium_chrome")
    options.add_experimental_option("prefs", {
        "profile.content_settings.exceptions.clipboard": {
            "[*.]sharepoint.com,*": {"setting": 1},
            "[*.]live.com,*":       {"setting": 1},
        }
    })

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        print("Opening SharePoint folder...")
        driver.get(SHAREPOINT_FOLDER_URL)

        print("Waiting for file list to load (log in if prompted)...")
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH,
                "//div[@role='grid' or @data-automationid='list-page']"
            ))
        )
        print("File list loaded.\n")

        results = {}
        errors  = []

        for idx, (row_index, filename) in enumerate(targets):
            print(f"  [{idx+1}/{len(targets)}] {filename} ...", end=" ", flush=True)

            url, err = get_share_link_for_file(driver, filename)

            if url:
                results[row_index] = url
                print("✓")
            else:
                print(f"✗ {err}")
                errors.append(f"{filename}: {err}")

            # Save progress after every file
            if results:
                patch_csv(CSV_PATH, rows, headers, results)

        print(f"\n{'='*60}")
        print(f"Done. Updated {len(results)} / {len(targets)} rows.")
        print(f"CSV saved: {CSV_PATH}")
        if errors:
            print(f"\n⚠  {len(errors)} error(s):")
            for e in errors:
                print(f"   • {e}")
        print("="*60)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()