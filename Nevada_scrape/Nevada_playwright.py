import time
import re
from bs4 import BeautifulSoup as Bs
from lxml import etree
from tqdm import tqdm
from playwright.sync_api import sync_playwright
import json

def extract_bid_information(context, page):    
    # pagination
    nevada_search_soup = Bs(page.content(), "html.parser")
    dom = etree.HTML(str(nevada_search_soup))
    
    total_records = nevada_search_soup.find('span', class_="ui-paginator-current").text.split()[-1]
    page_count = int(total_records)//25
   
    bid_collection = {}       

    detail_page = context.new_page()
        
    # Iterating over all pages
    for p in range(1, page_count+1):
        print(f"------------ Result Page {p} ---------------")               
        rows = nevada_search_soup.find('tbody', class_='ui-datatable-data ui-widget-content').find_all('tr')                
            
        for row in tqdm(rows):
            try:
                bid_info = {}
                # Extracting First page
                td_row = row.find_all('td')
                bid_solicitation_col = td_row[0].find('a')                
                bid_solicitation_name, bid_solicitation_url = bid_solicitation_col.text, "https://nevadaepro.com" + bid_solicitation_col.get('href')
                buyer = td_row[5].text  
                description = td_row[6].text
                bid_opening_date = td_row[7].text
                
                # Extracting header information from bid info detail page
                header_information = {}                
            
                detail_page.goto(bid_solicitation_url)
                time.sleep(2) 
                    
                bid_detail_soup = Bs(detail_page.content(), "html.parser")
                
                bid_dom = etree.HTML(str(bid_detail_soup))
                
                header_keys = bid_dom.xpath("//td[.='Header Information']/../..//td[@class='t-head-01']/text()")
                header_values = bid_dom.xpath("//td[.='Header Information']/../..//td[@class='tableText-01' or not(@class) and not(@colspan)]/text()")
                
                for key, value in zip(header_keys, header_values):
                    head_key = re.sub(r'[\n\t:]', '', key).strip()
                    head_value = re.sub(r'[\n\t]', '', value).strip()
                    header_information[head_key] = head_value

                    if "Bill-to Address" in head_key:
                        break
                
                bill_to_adress_value = ' '.join(bid_dom.xpath("//td[.='Bill-to Address:']/following-sibling::td[1]/text()"))
                header_information["Bill-to Address"] = re.sub(r'[\n\t:]', '', bill_to_adress_value).strip()
                
                bid_info = {
                    'Bid Solicitation #': bid_solicitation_name,
                    'bid_solicitation_url': bid_solicitation_url,
                    'Buyer': buyer,
                    'Description': description,
                    'Bid Opening Date': bid_opening_date,   
                    'header information': header_information,     
                    }
                print(bid_info)
                
                if bid_info:
                    bid_collection[bid_solicitation_name] = bid_info
                
                # Saving Files in bid_solocitation folder
                download_file_attachments(detail_page, bid_solicitation_name)
                
            except Exception as e:
                pass
                
        
        # clicking to next page
        next_btn = page.query_selector("//span[@class='ui-paginator-next ui-state-default ui-corner-all']")
        if next_btn:
            next_btn.click()
            time.sleep(2)            
            nevada_search_soup = Bs(page.content(), "html.parser")

    return bid_collection

def download_file_attachments(detail_page, bid_solicitation_name):
    try:
        documents =  detail_page.query_selector_all("//a[@class='link-01']")
        for document in documents:
            # Set download path for the current context
            download_folder = f"Nevada_scrape/Nevada_Files/{bid_solicitation_name}"
            detail_page.on("download", lambda download: download.save_as(f"{download_folder}/{download.suggested_filename}"))

            # Click the link to initiate the download
            document.click()
            
            print(f"{document.inner_text()} File downloaded")

    except Exception as e:
        print(e)

with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    page = context.new_page()
    
    # Replace with the Searching URL
    nevada_search_url = "https://nevadaepro.com/bso/view/search/external/advancedSearchBid.xhtml?openBids=true"
    # nevada_search_url = "https://nevadaepro.com/bso/view/search/external/advancedSearchContractBlanket.xhtml?q=as&currentDocType=contractBlankets"

    page.goto(nevada_search_url, wait_until="load")

    time.sleep(2)
    
    try:
        bid_collection = extract_bid_information(context, page)
    except Exception as e:
        pass
    
    with open('Nevada_scrape/nevada_data.json', 'w') as json_file:
        json.dump(bid_collection, json_file, indent=4)
    
    browser.close()


