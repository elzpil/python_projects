from bs4 import BeautifulSoup
import requests
from datetime import datetime
import os
import logging
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import config
import csv
import json

# constants
SITE_URL = "https://www.maxima.lt/pasiulymai"
HEADERS = {'User-Agent': 'Mozilla/5.0'}
CATEGORIES_FILE = 'kategorijos.txt'

def setup_logging():
    logging.basicConfig(filename='scraper.log', level=logging.INFO,
                        format='%(asctime)s:%(levelname)s:%(message)s')

def log_message(message, level='info'):
    # Log a message with the given level
    if level == 'info':
        logging.info(message)
    elif level == 'error':
        logging.error(message)
    elif level == 'debug':
        logging.debug(message)
    elif level == 'warning':
        logging.warning(message)
    elif level == 'critical':
        logging.critical(message)


def load_categories(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            categories = [line.strip() for line in file]
        log_message(f"Categories loaded from {filename}", 'info')
        return categories
    except Exception as e:
        log_message(f"Error loading categories from {filename}: {e}", 'error')
        raise


def parse_html(html_text):
    soup = BeautifulSoup(html_text, 'lxml')
    log_message("HTML content parsed with BeautifulSoup", 'info')
    return soup


def extract_items(soup):
    sections = soup.find_all('section', {'id': lambda x: x and x.startswith('offer_list_multiple')})
    filtered_items = []
    all_items =  []
    
    for section in sections:
        category = section.find('h2', class_='mb-3 mb-lg-4').text.strip()
        item_cards = section.find_all('div', class_='card-body offer-card d-flex flex-column')
        
        for item in item_cards:
            name = item.find('h4', class_='mt-4 text-truncate text-truncate--2').text.replace('\n','').strip()
            discount = item.find('div', class_='discount')
            special = item.find('div', class_='px-1 px-sm-2 px-lg-250 py-2 text-wrap d-flex align-items-center justify-content-center text-center text-white h-100 benefit-icon')

            if discount is not None:
                discount = discount.text.replace('\n', '').strip()
                discount_value = int(''.join(filter(str.isdigit, discount)))
            else:
                discount = ""
                discount_value = None

            if special is not None:
                special = special.text.replace('\n', '').strip()
            else:
                special = ""
            item_data = {
                    'name': name,
                    'discount': discount_value,
                    'special': special,
                    'category': category
                }
            all_items.append(item_data)
            #filtering
            if "vnt. už" in special:
                continue
            
            if (discount_value is not None and discount_value > 30) or ("vnt." not in special.lower() and special != ""):
                filtered_items.append(item_data)
    

    filtered_items.sort(key=lambda x: (x['discount'] is None, x['discount']), reverse=True)
    log_message(f"Extracted {len(all_items)} items, {len(filtered_items)} items after filtering", 'info')
    return filtered_items, all_items

def write_items_to_file(filename, filtered_items, all_items, categories_list):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            for item in filtered_items:
                if item['discount'] is not None:
                    file.write(f"{item['discount']}%   {item['name']}   {item['category']}\n")
                if item['special']:
                    file.write(f"{item['special']}   {item['name']}   {item['category']}\n")

            file.write("\nIŠ PASIRINKTŲ KATEGORIJŲ\n")
            for category in categories_list:
                file.write(f"\n{category}:\n")
                for item in all_items:
                    if item['category'] == category:
                        if item['discount'] is not None:
                            file.write(f"  {item['discount']}%   {item['name']}\n")
                        if item['special']:
                            file.write(f"  {item['special']}   {item['name']}\n")
        log_message(f"Results written to {filename}", 'info')
    except Exception as e:
        log_message(f"Error writing results to {filename}: {e}", 'error')
        raise

def fetch_html(url, headers):
    # Fetch the HTML content of a webpage
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.text

def fetch_html_with_retries(url, headers, retries=3, delay=5):
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            log_message(f"HTML content fetched from {url}", 'info')
            return response.text
        except requests.RequestException as e:
            log_message(f"Attempt {i + 1} failed: {e}", 'error')
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise

def send_email(subject, body, filename):
    # Send an email with the specified subject, body, and attachment
    try:
        msg = MIMEMultipart()
        msg['From'] = config.EMAIL_ADDRESS
        msg['To'] = config.RECIPIENT_EMAIL
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        attachment = open(filename, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(filename)}")
        msg.attach(part)

        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(config.EMAIL_ADDRESS, config.RECIPIENT_EMAIL, text)
        server.quit()
        log_message(f"Email sent to {config.RECIPIENT_EMAIL} with attachment {filename}", 'info')
    except Exception as e:
        log_message(f"Failed to send email: {e}", 'error')

def export_to_csv(filename, data):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    log_message(f"Data exported to {filename} in CSV format", 'info')

def export_to_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    log_message(f"Data exported to {filename} in JSON format", 'info')


def main():
    setup_logging()

    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join('results', f'results_{current_time}.txt')
    csv_filename = os.path.join('results', f'results_{current_time}.csv')
    json_filename = os.path.join('results', f'results_{current_time}.json')
    
    try:
        categories_list = load_categories(CATEGORIES_FILE)
        html_text = fetch_html_with_retries(SITE_URL, HEADERS)
        #html_text = requests.get(SITE_URL, headers=HEADERS).text
        soup = BeautifulSoup(html_text, 'lxml')
        filtered_items, all_items = extract_items(soup)
        write_items_to_file(filename,filtered_items, all_items, categories_list)
        #export_to_csv(csv_filename, filtered_items) 
        #export_to_json(json_filename, filtered_items)
        #send_email("Scraping Results", "The scraping task has been completed. Please find the attached results file.", filename)
    except Exception as e:
        log_message(f"An error occurred: {e}", 'error')

if __name__ == "__main__":
    main()
