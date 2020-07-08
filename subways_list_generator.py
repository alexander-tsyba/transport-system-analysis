# 1. Parse webpage with subways list
# 2. Generate text file with following pattern line by line: [city], [country]\n
# https://en.wikipedia.org/wiki/List_of_metro_systems

import urllib.request
from urllib.request import Request
import urllib.parse
import ssl
from bs4 import BeautifulSoup

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

req = Request('https://en.wikipedia.org/wiki/List_of_metro_systems', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ssl_context) as file:
    page = BeautifulSoup(file.read(), 'html.parser')
    subways_table = page.find('table')
    subways_list = list()
    for subway_info in subways_table.find_all('tr')[1:]:
        try:
            city = subway_info.find_all('td')[0].find('a').get_text()
            country = subway_info.find_all('td')[1].find('a').get_text()
            if country[0] == '[':
                continue
            subways_list.append(city + ', ' + country + '\n')
        except AttributeError:
            continue

with open('cities.txt', 'w', encoding='utf8') as file:
    file.writelines(subways_list)
