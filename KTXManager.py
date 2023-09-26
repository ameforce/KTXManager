from lib.LogManager.LogManager import LogManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
import time
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchFrameException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import UnexpectedAlertPresentException

from selenium.webdriver.remote.webelement import WebElement


class KTXManager:
    def __init__(self,
                 login_id: str, login_pw: str,
                 departure_location: str, arrival_location: str, departure_date: str, departure_time: int, minimum_time: int):
        self.default_url = 'https://www.letskorail.com/ebizprd/prdMain.do'
        self.login_url = 'https://www.letskorail.com/korail/com/loginProc.do'
        self.login_id = login_id
        self.login_pw = login_pw
        self.__departure_location = departure_location
        self.__arrival_location = arrival_location
        self.__departure_date = departure_date
        self.__departure_time = departure_time
        self.__minimum_time = minimum_time
        self.refine_departure_date(self.__departure_date)
        self.__browser = webdriver.Chrome()
        # self.loger = LogManager()
        return

    def refine_departure_date(self, date_string: str):
        date_object = None
        format_list = ['%Y%m%d', '%y%m%d', '%Y.%m.%d', '%y.%m.%d', '%Y-%m-%d', '%y-%m-%d']
        for format_string in format_list:
            try:
                date_object = datetime.strptime(date_string, format_string)
            except ValueError:
                continue
        if date_object is None:
            raise ValueError('Invalid Date Type')
        self.__departure_date = date_object.strftime('%Y%m%d')

    def close_popup(self) -> None:
        current_window = self.__browser.current_window_handle
        while len(self.__browser.window_handles) >= 2:
            for window in self.__browser.window_handles:
                if current_window != window:
                    self.__browser.switch_to.window(window)
                    self.__browser.close()
            self.__browser.switch_to.window(current_window)
        return

    def close_alert_popup(self) -> None:
        self.__browser.implicitly_wait(0)
        try:
            self.__browser.find_element(By.XPATH, '//*[@id="korail-alert"]/div[3]/button').click()
        except NoSuchElementException:
            pass
        self.__browser.implicitly_wait(5)
        return

    def move_browser(self, url: str) -> None:
        self.__browser.get(url)
        self.__browser.implicitly_wait(5)
        self.close_popup()
        return

    def login(self, login_id: str, login_pw: str) -> None:
        self.move_browser(self.login_url)
        self.__browser.find_element(By.XPATH, '//*[@id="header"]/div[1]/div/ul/li[2]/a/img').click()
        self.__browser.find_element(By.XPATH, '//*[@id="txtMember"]').send_keys(login_id)
        self.__browser.find_element(By.XPATH, '//*[@id="txtPwd"]').send_keys(login_pw)
        self.__browser.find_element(By.XPATH, '//*[@id="loginDisplay1"]/ul/li[3]/a/img').click()
        return

    def enter_info(self, departure_location: str, arrival_location: str, departure_time: str) -> None:
        info_dict = {
            '//*[@id="txtGoStart"]': departure_location,
            '//*[@id="txtGoEnd"]': arrival_location
        }
        for info_key in info_dict:
            element = self.__browser.find_element(By.XPATH, info_key)
            element.clear()
            element.send_keys(info_dict[info_key])

        # Select date
        current_window = self.__browser.current_window_handle
        self.__browser.find_element(By.XPATH, '//*[@id="res_cont_tab01"]/form/div/fieldset/ul[2]/li[1]/a/img').click()
        while len(self.__browser.window_handles) < 2:
            break
        self.__browser.switch_to.window(self.__browser.window_handles[1])
        self.__browser.find_element(By.XPATH, f'//*[@id="d{departure_time}"]').click()
        self.__browser.switch_to.window(current_window)

        # Select time
        time_drop_down = self.__browser.find_element(By.XPATH, '//*[@id="time"]')
        select = Select(time_drop_down)
        select.select_by_value(str(self.__departure_time))

        # click Reservation Button
        self.__browser.find_element(By.XPATH, '//*[@id="res_cont_tab01"]/form/div/fieldset/p/a/img').click()

        return

    def wait_queue(self):
        self.__browser.implicitly_wait(0)
        while True:
            try:
                self.__browser.find_element(By.XPATH, '//*[@id="NetFunnel_Skin_Top"]/img')
            except NoSuchElementException:
                break
        self.__browser.implicitly_wait(5)

    def select_ktx(self):
        self.__browser.implicitly_wait(0)
        while True:
            try:
                self.__browser.find_element(By.XPATH, '//*[@id="selGoTrainRa00"]').click()
                self.__browser.find_element(By.XPATH, '//*[@id="center"]/div[3]/p/a/img').click()
                break
            except NoSuchElementException:
                self.wait_queue()
                self.close_alert_popup()
        self.__browser.implicitly_wait(5)
        return

    def detect_valid_seat(self) -> WebElement or None:
        self.__browser.implicitly_wait(0)
        for i in range(10):
            for j in range(2):
                print(f'searching: [{i}][{j}]')
                try:
                    element = self.__browser.find_element(By.XPATH, f'//*[@id="tableResult"]/tbody/tr[{i+1}]/td[{j+5}]/img')
                except NoSuchElementException:
                    try:
                        element = self.__browser.find_element(By.XPATH, f'//*[@id="tableResult"]/tbody/tr[{i+1}]/td[{j+5}]/a/img')
                    except NoSuchElementException:
                        element = self.__browser.find_element(By.XPATH, f'//*[@id="tableResult"]/tbody/tr[{i+1}]/td[{j+5}]/a[1]/img')
                alt_value = element.get_attribute('alt')
                if alt_value != '좌석매진':
                    self.__browser.implicitly_wait(5)
                    return element
        self.__browser.implicitly_wait(5)
        return None

    def reservation(self, element: WebElement) -> bool:
        element.click()
        # On frame detection
        try:
            self.__browser.switch_to.frame('embeded-modal-traininfo')
            self.__browser.find_element(By.XPATH, '/html/body/div/div[2]/p[3]/a').click()
        except NoSuchFrameException:
            pass
        except UnexpectedAlertPresentException:
            pass

        # On alert detection
        while True:
            try:
                self.__browser.switch_to.alert.accept()
            except NoAlertPresentException:
                break

        self.__browser.switch_to.default_content()

        # If no seats remain
        try:
            self.__browser.find_element(By.XPATH, '//*[@id="contents"]/div[1]/div[2]/div/p[2]/a').click()
            return False
        except NoSuchElementException:
            pass
        return True

    def logic(self) -> None:
        self.login(self.login_id, self.login_pw)
        self.move_browser(self.default_url)
        self.enter_info(self.__departure_location, self.__arrival_location, self.__departure_date)
        self.wait_queue()
        element = None
        while True:
            while True:
                self.select_ktx()
                self.wait_queue()
                element = self.detect_valid_seat()
                if element is not None:
                    break
            if self.reservation(element):
                break
            print('check')
        print('yeah')
        return

