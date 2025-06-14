import asyncio
import logging
import os
import subprocess
from datetime import datetime
from random import randint
from urllib.parse import urljoin

import aiohttp
import bs4
import db
import fake_useragent
from playwright.async_api import Browser, async_playwright
from settings import BASE_URL, DATABASE_DUMPS_PATH, PHONE_NUMBER_API_URL, RESULTS_PER_PAGE
from utils import get_user_secure_data

logger = logging.getLogger(__name__)


async def fetch_first_page_and_return_html_with_pages_count(browser: Browser):
    """
    Fetch the first page of the car listings and return the HTML content along with the total number of pages.
    """
    page = await browser.new_page()

    try:
        await page.goto(urljoin(BASE_URL, f"?page=0&countpage={RESULTS_PER_PAGE}"))
        await page.wait_for_selector("span#staticResultsCount")

        text = await page.inner_text("span#staticResultsCount")
        results_count = int(text.replace(" ", "").strip())
        html = await page.content()
        return html, results_count // RESULTS_PER_PAGE + (results_count % RESULTS_PER_PAGE > 0)
    except Exception as e:
        logger.error(f"Error fetching the first page: {e}")
        return "", 0
    finally:
        await page.close()


def get_cars_urls(html):
    """
    Extract car URLs from the HTML content of the given page.
    """
    soup = bs4.BeautifulSoup(html, "lxml")
    car_sections = soup.select("section.ticket-item")
    car_urls = [section.select_one("a.address").get("href") for section in car_sections]
    return car_urls


async def fetch_page(session, page_number=1):
    """
    Fetch a page using aiohttp with a random user agent.
    """
    headers = {"User-Agent": fake_useragent.UserAgent().random}
    params = {"page": page_number, "countpage": RESULTS_PER_PAGE}
    async with session.get(BASE_URL, headers=headers, params=params) as response:
        if response.status == 200:
            return await response.text()
        else:
            logger.error(f"Failed to fetch page {page_number}: {response.status}")


async def fetch_page_and_get_cars_urls(session, page_number):
    """
    Fetch a page and extract car URLs from it.
    """
    html = await fetch_page(session, page_number)
    return get_cars_urls(html)


async def fetch_with_retry(session, url, retries=3, delay=2, response_type="text"):
    """
    Fetch a URL with retries in case of failure.
    """
    headers = {"User-Agent": fake_useragent.UserAgent().random}
    for attempt in range(retries):
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    if response_type == "text":
                        return await response.text()
                    elif response_type == "json":
                        return await response.json()
                else:
                    logger.error(f"Failed to fetch {url}: {response.status}")
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
        await asyncio.sleep(delay + randint(2, 4))
    return None


async def parse_car_details(browser: Browser, session, car_url):
    if await db.check_if_car_exists(car_url):
        logger.info(f"Car already exists in the database: {car_url}")
        return

    page = await browser.new_page()
    try:
        logger.info(f"Parsing car details from {car_url}")
        await page.goto(car_url)
        await page.wait_for_selector("a.phone_show_link")
        await page.click("a.phone_show_link")

        html = await page.content()
        soup = bs4.BeautifulSoup(html, "lxml")
        data_hash, data_expires = get_user_secure_data(soup)

        notice = soup.select_one("div.notice_head")
        if notice and "видалене" in notice.get_text(strip=True):
            logger.info(f"Car listing has been removed: {car_url}")
            return

        title = soup.select_one("h1.head").get_text(strip=True)
        price = soup.select_one("div.price_value").select_one("strong").get_text(strip=True)
        if "$" not in price:
            price = soup.select_one("div.price_value--additional span i-block span[data-currency='USD']").get_text(
                strip=True
            )
        price_usd = int(price.replace(" ", "").replace("$", ""))
        odometer = int(soup.select_one("div.base-information span").get_text(strip=True)) * 1000
        username = soup.select_one(".seller_info_name").get_text(strip=True)
        if seller_link := soup.select_one(".seller_info_name a"):
            username = seller_link.get("href", "").split("/")[-1].split(".html")[0]
        image_url = soup.select_one("div.carousel-inner div picture img").get("src")
        images_count = int(
            soup.select_one("div.count-photo.left span.count span.mhide").get_text(strip=True).split(" ")[1]
        )
        vin_code_element = soup.select_one("span.label-vin") or soup.select_one("span.vin-code")
        car_vin = vin_code_element.get_text(strip=True) if vin_code_element else "N/A"
        car_number_element = soup.select_one("span.state-num")
        car_number = (
            car_number_element.find(string=True, recursive=False).strip().replace(" ", "")
            if car_number_element
            else "N/A"
        )

        car_id = car_url.split("_")[-1].split(".")[0]
        raw_phone_number = await fetch_with_retry(
            session,
            PHONE_NUMBER_API_URL.format(car_id=car_id, hash=data_hash, expires=data_expires),
            retries=5,
            delay=5,
            response_type="json",
        )
        raw_phone_number = raw_phone_number.get("formattedPhoneNumber", "")
        if not raw_phone_number:
            logger.error(f"Phone number not found for car: {car_url}")
            return
        phone_number = int(f"38{''.join(filter(str.isdigit, raw_phone_number))}")

        await db.insert_car(
            car_url,
            title,
            price_usd,
            odometer,
            username,
            phone_number,
            image_url,
            images_count,
            car_number,
            car_vin,
        )
        logger.info(f"Car details saved to the database: {car_url}")

    except Exception as e:
        logger.error(f"Error parsing car details from {car_url}: {e}")
    finally:
        await page.close()


async def limited_parse_car_details(browser: Browser, session, car_url, semaphore):
    """
    Parse car details with a semaphore to limit concurrent requests.
    """
    async with semaphore:
        return await parse_car_details(browser, session, car_url)


async def main():
    """Main function to run the parser."""
    async with aiohttp.ClientSession() as session:
        async with async_playwright() as p:
            await db.init_db_pool()
            semaphore = asyncio.Semaphore(10)
            browser = await p.chromium.launch(headless=True)

            try:
                first_page_html, pages_count = await fetch_first_page_and_return_html_with_pages_count(browser)
                logger.info(f"Total pages found: {pages_count}")

                fetch_cars_urls_tasks = [
                    fetch_page_and_get_cars_urls(session, page_number) for page_number in range(1, pages_count + 1)
                ]
                cars_urls = await asyncio.gather(*fetch_cars_urls_tasks, return_exceptions=True)
                first_page_cars_urls = get_cars_urls(first_page_html)
                cars_urls = first_page_cars_urls + [url for sublist in cars_urls for url in sublist]
                logger.info(f"Total cars URLs found: {len(cars_urls)}")

                parse_and_save_to_db_tasks = [
                    limited_parse_car_details(browser, session, car_url, semaphore) for car_url in cars_urls
                ]
                await asyncio.gather(*parse_and_save_to_db_tasks, return_exceptions=True)

                logger.info("All car details have been parsed and saved to the database.")

                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                os.makedirs(DATABASE_DUMPS_PATH, exist_ok=True)
                dump_file_path = os.path.join(DATABASE_DUMPS_PATH, f"dump_{timestamp}.sql")

                subprocess.run(
                    ["pg_dump", "--data-only", "--inserts", "--column-inserts", "-f", dump_file_path, db.DATABASE_URL],
                    check=True,
                )
                logger.info(f"Database dump saved to {dump_file_path}")
            except Exception as e:
                logger.error(f"An error occurred during parsing: {e}")
            finally:
                await browser.close()
                await db.db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
