import os

from dotenv import load_dotenv
from requests import Session, Response
from bs4 import BeautifulSoup
from tabulate import tabulate

load_dotenv()


class Parser:
    def __init__(self):
        self.BASE_URL = os.getenv("URL")
        self.session = Session()
        self.token = None
    
    def _get_html(self, response: Response) -> BeautifulSoup:
        """Получаем чистый HTML"""
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
    
    def _update_token(self, response: Response):
        """На каждой странице обновляем токен"""
        soup = self._get_html(response)
        token = soup.find("input", {"name": "token"})
        if token:
            self.token = token.get("value")

    def collect_data(self, list_data: list) -> dict[str]:
        for div in list_data:
            name = div.get("name")
            value = div.get("value")
            if name == "token":
                self.token = value
        return self.token
    
    def authorization(self) -> Response:
        """Проходим авторизацию"""
        login_page = self.session.get(self.BASE_URL)
        soup = self._get_html(login_page)

        list_data = soup.find_all("input")
        self.collect_data(list_data)
        
        auth_data = {
            'pma_username': os.getenv("LOGIN"),
            'pma_password': os.getenv("PASSWORD"),
            'server': '1',
            'token': self.token
        }
        form = soup.find("form").get("action")
        submit_url = f"{self.BASE_URL}/{form}"
        next_page = self.session.post(submit_url, data=auth_data)
        self._update_token(next_page)
        return next_page
    
    def get_database(self, auth_page: Response) -> Response:
        """Ищем нужную БД"""
        href = None
        soup = self._get_html(auth_page)
        link_list = soup.find_all("a", class_ = "nav-link text-nowrap")
        for link in link_list:
            if link.find("img", title="Databases"):
                href = link["href"]
        submit_link = f"{self.BASE_URL}/{href}"
        next_page = self.session.post(submit_link, data={"token": self.token})
        self._update_token(next_page)
        return next_page
    
    def get_db_info(self, db_page: Response) -> Response:
        """Переходим в нужную БД"""
        soup = self._get_html(db_page)
        href = soup.find("a", title="Jump to database 'testDB'")["href"]
        info_data = {
            'db': 'testDB',
            'token': self.token
        }
        submit_link = f"{self.BASE_URL}/{href}"
        next_page = self.session.post(submit_link, data=info_data)
        self._update_token(next_page)
        return next_page
    
    def get_db_table_info(self, db: Response) -> Response:
        """Переходим в таблицу"""
        href = None
        soup = self._get_html(db)
        img = soup.find("img", title="Browse")
        if img:
            a_tag = img.find_parent("a")
            if a_tag:
                href = a_tag["href"]

        data = {
            'db': 'testDB',
            'table': 'users',
            'token': self.token
        }
        submit_link = f"{self.BASE_URL}/{href}"
        next_page = self.session.post(submit_link, data=data)
        self._update_token(next_page)
        return next_page
    
    def parse_db(self, db_table: Response) -> str:
        """Парсим таблицу и выводим результат"""
        soup = self._get_html(db_table)
        name_list = soup.find_all("td", class_ = ["data", "grid_edit", "click2", "pre_wrap"])
        names = [name.get_text(strip=True) for name in name_list]
        json = [
            {
                "name": names[i],
                "id": names[i+1]
            } for i in range (0, len(names), 2)
        ]
        table = [[name["id"], name["name"]] for name in json]
        print(tabulate(table, headers=["ID", "Имя"], tablefmt="grid"))
    
    def start_parsing(self):
        authorization_page = self.authorization()
        database_page = self.get_database(authorization_page)
        database_list = self.get_db_info(database_page)
        get_db_info = self.get_db_table_info(database_list)
        result = self.parse_db(get_db_info)
        return result

if __name__ == "__main__":
    parser = Parser()
    parser.start_parsing()