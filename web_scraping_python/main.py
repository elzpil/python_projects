from bs4 import BeautifulSoup
import requests
from datetime import datetime
import os

site = "https://www.maxima.lt/pasiulymai"
hdr = {'User-Agent': 'Mozilla/5.0'}
html_text = requests.get(site, headers=hdr).text
soup = BeautifulSoup(html_text, 'lxml')

def load_categories(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        categories = [line.strip() for line in file]
    return categories

def find():
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join('results', f'results_{current_time}.txt')
    categories_file = 'kategorijos.txt'
    categories_list = load_categories(categories_file)
    
    sections = soup.find_all('section', {'id': lambda x: x and x.startswith('offer_list_multiple')})

    items = []
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

            all_items.append({
                    'name': name,
                    'discount': discount_value,
                    'special': special,
                    'category': category
                })
            #filtering
            if "vnt. už" in special:
                continue
            
            if (discount_value is not None and discount_value > 30) or ("vnt." not in special.lower() and special != ""):
                items.append({
                    'name': name,
                    'discount': discount_value,
                    'special': special,
                    'category': category
                })
    

    items.sort(key=lambda x: (x['discount'] is None, x['discount']), reverse=True)
    write_to_file(items, all_items, filename, categories_list)

def write_to_file(items, all_items, filename, categories_list):
    with open(filename, 'w', encoding='utf-8') as file:
        for item in items:
            if item['discount'] is not None:
                file.write(f"{item['discount']}%   {item['name']}   {item['category']}\n\n")
            if item['special'] != "":
                file.write(f"{item['special']}   {item['name']}   {item['category']}\n\n")

        file.write("\nIŠ PASIRINKTŲ KATEGORIJŲ\n")
    
        for c in categories_list:
            file.write(f"{c}\n")
            for item in all_items:
                if item['category'] == c:
                    if item['discount'] is not None:
                        file.write(f"{item['discount']}%   {item['name']}\n")
                    if item['special'] != "":
                        file.write(f"{item['special']}   {item['name']}\n")
               
find()
