from bs4 import BeautifulSoup
import requests
from datetime import datetime
import os

site= "https://www.maxima.lt/pasiulymai"
hdr = {'User-Agent': 'Mozilla/5.0'}
html_text = requests.get(site, headers=hdr).text
soup = BeautifulSoup(html_text, 'lxml')

def find():
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join('results', f'results_{current_time}.txt')
    item_cards = soup.find_all('div', class_='card-body offer-card d-flex flex-column')

    with open(filename, 'w', encoding='utf-8') as file:
        for item in item_cards:
            name = item.find('h4', class_='mt-4 text-truncate text-truncate--2').text.replace('\n','').strip()
            discount = item.find('div', class_='discount')
            special = item.find('div', class_='px-1 px-sm-2 px-lg-250 py-2 text-wrap d-flex align-items-center justify-content-center text-center text-white h-100 benefit-icon')

            if discount is not None:
                discount = discount.text.replace('\n', '').strip()
                discount_value = int(''.join(filter(str.isdigit, discount)))
            else:
                discount = ""

            if special is not None:
                special = special.text.replace('\n', '').strip()
            else:
                special = ""
                
            if "vnt. už" in special:
                continue
                
            if (discount_value is not None and discount_value > 30) or ("vnt." not in special.lower() and special != ""):
                if discount != "":
                    file.write(f"{discount_value}%   {name}\n\n")
        
                if special != "":
                    file.write(f"{special}    {name}\n\n")
                    
            
find()

