import requests
from bs4 import BeautifulSoup as Bs
import re
import os
import json
from concurrent.futures import ThreadPoolExecutor

class BidScraper:
    def __init__(self):
        self.cookies = {}
        self.headers = {}
        print("BidScraper initialized")

    def fetch_cookies(self):
        response = requests.get('https://nevadaepro.com/bso/view/search/external/advancedSearchBid.xhtml?openBids=true')
        soup = Bs(response.text, 'lxml')
        pagination = soup.find('span', class_="ui-paginator-current")
        records = pagination.text.split(" ")[-1]
        self.cookies = response.cookies.get_dict()
        print(f"Cookies fetched: {self.cookies}")
        return records

    def get_bid_data(self, links, base_url):
        print("Fetching bid data...")
        response_data = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.process_bid_link, base_url + link, response_data) for link in links]
            for future in futures:
                future.result()
        
        with open('Nevada_scrape/nevada_optimised_data.json', 'w') as json_file:
            json.dump(response_data, json_file, indent=4)
        print("Bid data fetched and saved to json")

    def process_bid_link(self, url, response_data):
        print(f"Processing bid link: {url}")
        data_dict, updated_dict = {}, {}
        res = requests.get(url)
        soup = Bs(res.text, 'html.parser')
        table = soup.find('table', class_="table-01")
        table_data = table.find_all('td', class_='t-head-01')

        for td_head in table_data:
            key = td_head.get_text(strip=True)
            value_td = td_head.find_next_sibling('td')
            if value_td:
                value = value_td.get_text(strip=True)
                data_dict[key] = value

        for key, values in data_dict.items():
            updated_key = key.replace(":", " ").replace("\n", "").strip()
            updated_value = values.strip()
            updated_dict[updated_key] = updated_value
            if updated_key == "Bill-to Address":
                break

        response_data[updated_dict['Bid Number']] = updated_dict
        print(f"Processed data for bid number {updated_dict['Bid Number']}")
        urls = table.find_all('a', class_="link-01")
        filtered_data = [(url['href'], url.text) for url in urls if 'javascript:downloadFile' in url['href']]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.download_file, *self.construct_download_data(url, text, updated_dict)) for url, text in filtered_data]
            for future in futures:
                future.result()

    def construct_download_data(self, url, text, updated_dict):
        pattern = r"javascript:downloadFile\('(\d+)'\)"
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            data = {
                '_csrf': self.cookies['XSRF-TOKEN'],
                'mode': 'download',
                'bidId': updated_dict['Bid Number'],
                'docId': updated_dict['Bid Number'],
                'currentPage': '1',
                'querySql': '',
                'downloadFileNbr': file_id,
                'itemNbr': 'undefined',
                'parentUrl': f'close/{file_id}',
                'fromQuote': '',
                'destination': '',
            }
            print(f"Constructed download data for file id {file_id}")
            return 'https://nevadaepro.com/bso/external/bidDetail.sdo', data, updated_dict['Bid Number'], text

    def download_file(self, url, data, bid_number, text):
        print(f"Downloading file for bid number {bid_number}")
        response = requests.post(url, cookies=self.cookies, headers=self.headers, data=data)
        if response.status_code == 200:
            nevada_dir = os.getcwd() + "/Nevada_optimised_Files"
            directory_path = os.path.join(nevada_dir, str(bid_number))
            os.makedirs(directory_path, exist_ok=True)
            file_extension = 'docx' if text.endswith('.docx') else 'pdf'
            file_path = os.path.join(directory_path, f"{text}.{file_extension}")
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"File downloaded and saved to {file_path}")
            return file_path
        else:
            print(f"Failed to download file for bid number {bid_number}")

    def fetch_record_urls(self, records):
        print("Fetching record URLs...")
        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'bidSearchResultsForm:bidResultId',
            'javax.faces.partial.execute': 'bidSearchResultsForm:bidResultId',
            'javax.faces.partial.render': 'bidSearchResultsForm:bidResultId',
            'bidSearchResultsForm:bidResultId': 'bidSearchResultsForm:bidResultId',
            'bidSearchResultsForm:bidResultId_pagination': 'true',
            'bidSearchResultsForm:bidResultId_first': '0',
            'bidSearchResultsForm:bidResultId_rows': records,
            'bidSearchResultsForm:bidResultId_encodeFeature': 'true',
            'bidSearchResultsForm': 'bidSearchResultsForm',
            '_csrf': self.cookies['XSRF-TOKEN'],
            'openBids': 'true',
        }

        self.headers = {
            'authority': 'nevadaepro.com',
            'accept': 'application/xml, text/xml, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'faces-request': 'partial/ajax',
            'origin': 'https://nevadaepro.com',
            'referer': 'https://nevadaepro.com/bso/view/search/external/advancedSearchBid.xhtml?openBids=true',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }

        response = requests.post(
            'https://nevadaepro.com/bso/view/search/external/advancedSearchBid.xhtml',
            cookies=self.cookies,
            headers=self.headers,
            data=data,
        )
        soup = Bs(response.text, features="xml")
        html_data = soup.find('update').text
        html_soup = Bs(html_data, 'html.parser')
        hrefs = html_soup.find_all('a')
        links = [a.get('href') for a in hrefs if "purchaseorder" not in a.get('href') and "parentUrl=close" in a.get('href')]

        print(f"Fetched {len(links)} record URLs")
        return links, self.headers['origin']

if __name__ == "__main__":
    scraper = BidScraper()
    records = scraper.fetch_cookies()
    print(f"Number of records to process: {records}")
    links, base_url = scraper.fetch_record_urls(records)
    scraper.get_bid_data(links, base_url)
    print("Scraping completed")
