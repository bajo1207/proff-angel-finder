import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from typing import List, Tuple

file_name = "investor_list.md"

class WebScraper:
    def __init__(self, start_url: str):
        self.driver = webdriver.Chrome()
        self.start_url = start_url

    def accept_cookies(self):
        """Accepts the cookies on the page."""
        try:
            cookie_accept_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//button[@class="sc-ifAKCX bDpbwf" and text()="ENIG"]'))
            )
            cookie_accept_button.click()
        except TimeoutException as e:
            print(f"Timeout when accepting the cookie: {e}")

    def navigate_to_owners_page(self):
        """Navigates to the owner's page."""
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[.//span[text()="Roller og Eiere"]]'))
            )
            element.click()
        except TimeoutException as e:
            print(f"Timeout when looking for Roller og Eiere: {e}")

    def show_all_investors(self):
        """Shows all the investors."""
        try:
            button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//a[.//span[text()="Vis alle aksjonærer"]]'))
            )
            button.click()
        except TimeoutException as e:
            print(f"Timeout when clicking the Vis alle aksjonærer button: {e}")

    def click_more_until_end(self):
        """Continues to click the 'more' button until the end."""
        while True:
            try:
                more_button = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//a[.//span[text()="Vis flere"]]'))
                )
                more_button.click()
            except TimeoutException:
                break

    def extract_investor_data_and_links(self) -> List[Tuple[str, str, str, str]]:
        """Extracts the data and links of the investors."""
        investor_list = []
        try:
            table = self.driver.find_element(By.XPATH, '(//table[@class="shareholder-reg-table ui-wide"])[1]')
            rows = table.find_elements(By.XPATH, './tr')

            for row in rows[1:]:
                cols = row.find_elements(By.XPATH, './td')

                if len(cols) >= 4 and re.search('AS\\n', cols[0].text):
                    org_and_name = cols[0].text
                    share_percentage = cols[3].text
                    name = org_and_name.split('\nOrg nr')[0]
                    org_nr = org_and_name.split('\nOrg nr')[1]

                    link_elements = cols[0].find_elements(By.XPATH, './div/a')
                    if link_elements:
                        link = link_elements[0].get_attribute('href')
                        investor_list.append((name, share_percentage, link, org_nr))

        except TimeoutException as e:
            print(f"Timeout when extracting name and share percentage: {e}")

        return investor_list

    def extract_owner_list(self, table):
        """Extracts owner list from a given table."""
        rows = table.find_elements(By.XPATH, './tr')
        owner_list = []
        for row in rows[1:]:
            cols = row.find_elements(By.XPATH, './td')
            if len(cols) >= 4:
                name = cols[0].text
                share_percentage = float(cols[3].text[:-1].strip().replace(',', '.'))
                owner_list.append({"name": name, "percentage": share_percentage})
        return owner_list

    def extract_other_investments(self, table):
        """Extracts other investments from a given table."""
        rows = table.find_elements(By.XPATH, './tr')
        other_investments = []
        for row in rows[1:]:
            cols = row.find_elements(By.XPATH, './td')
            if len(cols) >= 4:
                name = cols[0].text.split('\nOrg nr')[0]
                other_investments.append(name)
        return other_investments

    def check_other_investments(self, url: str):
        """Checks other investments for a given URL."""
        self.driver.get(url)
        
        try:
            first_table = self.driver.find_element(By.XPATH, '(//table)[1]')
            owner_list = self.extract_owner_list(first_table)

            second_table = self.driver.find_element(By.XPATH, '(//table)[2]')
            other_investments = self.extract_other_investments(second_table)

            self.driver.back()

            significant_ownership = all([owner["percentage"] > 15 for owner in owner_list]) or any([owner["percentage"] > 40 for owner in owner_list])

            return (other_investments if len(other_investments) > 2 else None,
                    owner_list if significant_ownership else None)
                    
        except TimeoutException as e:
            print(f"Timeout when checking the first table: {e}")

    def scrape(self):
        """Main scraping function."""
        self.driver.get(self.start_url)
        self.accept_cookies()
        self.navigate_to_owners_page()
        self.show_all_investors()
        self.click_more_until_end()
        self.process_investor_data()
        
    

    def process_investor_data(self):
        """Processes the investor data."""
        investor_data = self.extract_investor_data_and_links()
        document = "# Potential Angel Investors\n\n"
        for name, share_percentage, link, org_nr in investor_data:
            other_investments, owner_list = self.check_other_investments(link)

            if other_investments:
                owned_by_table = ""
                if owner_list:
                    owned_by_table = "\n".join([f"| {owner['name']} | {owner['percentage']}% |" for owner in owner_list])

                other_investments_list = "\n".join([f"- {investment}" for investment in other_investments])

                document += f"### {name} ({org_nr})\n*Owns {share_percentage} of the company*\n\n### Owned by\n| Name | Percentage |\n| --- | --- |\n{owned_by_table}\n\n### Other investments\n{other_investments_list}\n\n"
        create_markdown_file(file_name, document)


def create_markdown_file(filename, content):
        with open(f"{filename}", "w") as file:
            file.write(content)
            
if __name__ == '__main__':
    scraper = WebScraper("https://www.proff.no/selskap/strise-as/trondheim/internettdesign-og-programmering/IF6R01G0C2C/")
    investor_data = scraper.scrape()