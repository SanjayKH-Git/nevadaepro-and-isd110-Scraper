import requests
from bs4 import BeautifulSoup as Bs
from lxml import etree
import csv
import re

def extract_isd(isd_search_url):
    isd_search_resp = requests.get(isd_search_url,  headers={'User-Agent': 'Mozilla/5.0'})
    isd_search_soup = Bs(isd_search_resp.text, "html.parser")
    dom = etree.HTML(str(isd_search_soup))

    # Get school details
    school_name = isd_search_soup.find('title').text.split('|')[1]
    address_text = isd_search_soup.find('p', class_='address').text.replace('Directions', '')
    address = re.sub(r'\s+', ' ', address_text.replace('\n', '')).strip()
    state = dom.xpath("(//a[contains(., 'Report Card')])[1]/text()")[0].split()[0]
    zip_code = address.split()[-1] 
    
    # Get Staff Details
    staff_data_list = []
    for p in range(7):
        page_url = f"{isd_search_url}?s=&page={p}"
        isd_search_resp = requests.get(page_url,  headers={'User-Agent': 'Mozilla/5.0'})
        isd_search_soup = Bs(isd_search_resp.text, "html.parser")
        
        print(f"------------------------------ Page: {p+1} ------------------------------")
        card_list = isd_search_soup.find_all('div', class_='views-row')
        for card in card_list:
            name = card.find('h2').text
            first_name, last_name = set(name.split(', '))
            title = card.find('div', class_='field job-title').text.strip()
            
            staff_data = [first_name, last_name, title, school_name, address, state, zip_code, page_url]
            print(staff_data)
            staff_data_list.append(staff_data)
    
    return staff_data_list
            
if __name__ == "__main__":    
    isd_search_url = "https://isd110.org/our-schools/laketown-elementary/staff-directory"
    
    staff_data_list = extract_isd(isd_search_url)
    
    # Writing data into csv
    header = ["First Name", "Last Name", "Title", "School Name", "Address", "State", "zip", "Page URL"]
    with open("isd110/isd_output.csv", "w", newline="", encoding="utf-8") as output_csv:
      csvwriter = csv.writer(output_csv)
      csvwriter.writerow(header)
      csvwriter.writerows(staff_data_list)
    
