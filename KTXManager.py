from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchFrameException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import UnexpectedAlertPresentException
from lib.LogManager.LogManager import LogManager
from datetime import datetime
import multiprocessing
import time


class KTXManager:
    def __init__(self,
                 login_id: str, login_pw: str,
                 departure_location: str, arrival_location: str, departure_date: str, departure_time: int, limit_time: int):
        self.__default_url = 'https://www.letskorail.com/ebizprd/prdMain.do'
        self.login_url = 'https://www.letskorail.com/korail/com/loginProc.do'
        self.login_id = login_id
        self.login_pw = login_pw
        self.__departure_location = departure_location
        self.__arrival_location = arrival_location
        self.__departure_date = departure_date
        self.__departure_time = departure_time
        self.__limit_time = limit_time
        self.refine_departure_date(self.__departure_date)
        # self.__browser = webdriver.Chrome()
        self.__driver = []
        self.__search_time_list = []
        self.__process_num = None
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

    def __calc_need_process(self) -> int:
        return self.__limit_time - self.__departure_time

    def __time_param_splitter(self, process_count: int) -> list[int]:
        search_time_list = []
        for i in range(process_count):
            search_time_list.append(int(self.__departure_time) + i)
        return search_time_list

    def __param_recombinator(self, process_count: int) -> [(int, int)]:
        param_list = []
        search_time_list = self.__time_param_splitter(process_count)
        for i in range(process_count):
            param_list.append((i, search_time_list[i]))
        return param_list

    @staticmethod
    def __close_popup(driver: webdriver.Chrome) -> None:
        current_window = driver.current_window_handle
        while len(driver.window_handles) >= 2:
            for window in driver.window_handles:
                if current_window != window:
                    driver.switch_to.window(window)
                    driver.close()
            driver.switch_to.window(current_window)
        return

    def __move_url(self, driver: webdriver.Chrome, target_url: str) -> None:
        driver.get(target_url)
        driver.implicitly_wait(5)
        self.__close_popup(driver)
        return

    def __login(self, driver: webdriver.Chrome) -> None:
        self.__move_url(driver, self.login_url)
        driver.find_element(By.XPATH, '//*[@id="header"]/div[1]/div/ul/li[2]/a/img').click()
        driver.find_element(By.XPATH, '//*[@id="txtMember"]').send_keys(self.login_id)
        driver.find_element(By.XPATH, '//*[@id="txtPwd"]').send_keys(self.login_pw)
        driver.find_element(By.XPATH, '//*[@id="loginDisplay1"]/ul/li[3]/a/img').click()
        return

    def __enter_info(self, driver: webdriver.Chrome, search_time: int) -> None:
        info_dict = {
            '//*[@id="txtGoStart"]': self.__departure_location,
            '//*[@id="txtGoEnd"]': self.__arrival_location
        }
        for info_key in info_dict:
            element = driver.find_element(By.XPATH, info_key)
            element.clear()
            element.send_keys(info_dict[info_key])

        # Select date
        current_window = driver.current_window_handle
        driver.find_element(By.XPATH, '//*[@id="res_cont_tab01"]/form/div/fieldset/ul[2]/li[1]/a/img').click()
        while len(driver.window_handles) < 2:
            break
        driver.switch_to.window(driver.window_handles[1])
        driver.find_element(By.XPATH, f'//*[@id="d{self.__departure_date}"]').click()
        driver.switch_to.window(current_window)

        # Select time
        time_drop_down = driver.find_element(By.XPATH, '//*[@id="time"]')
        select = Select(time_drop_down)
        select.select_by_value(str(search_time))

        # click Reservation Button
        driver.find_element(By.XPATH, '//*[@id="res_cont_tab01"]/form/div/fieldset/p/a/img').click()
        return

    @staticmethod
    def __wait_queue(driver: webdriver.Chrome) -> None:
        driver.implicitly_wait(0)
        while True:
            try:
                driver.find_element(By.XPATH, '//*[@id="NetFunnel_Skin_Top"]/img')
            except NoSuchElementException:
                break
        driver.implicitly_wait(5)
        return

    @staticmethod
    def __close_alert_popup(driver: webdriver.Chrome) -> None:
        driver.implicitly_wait(0)
        try:
            driver.find_element(By.XPATH, '//*[@id="korail-alert"]/div[3]/button').click()
        except NoSuchElementException:
            pass
        driver.implicitly_wait(5)
        return

    def __select_ktx(self, driver: webdriver.Chrome) -> None:
        driver.implicitly_wait(0)
        while True:
            try:
                driver.find_element(By.XPATH, '//*[@id="selGoTrainRa00"]').click()
                driver.find_element(By.XPATH, '//*[@id="center"]/div[3]/p/a/img').click()
                break
            except NoSuchElementException:
                self.__wait_queue(driver)
                self.__close_alert_popup(driver)
        driver.implicitly_wait(5)
        return

    def __detect_valid_seat(self, driver: webdriver.Chrome) -> WebElement or None:
        driver.implicitly_wait(0)
        for i in range(10):
            for j in range(2):
                print(f'\tsearching: [{self.__process_num}] - [{i}][{j}]')
                try:
                    element = driver.find_element(By.XPATH,
                                                  f'//*[@id="tableResult"]/tbody/tr[{i + 1}]/td[{j + 5}]/img')
                except NoSuchElementException:
                    try:
                        element = driver.find_element(By.XPATH,
                                                      f'//*[@id="tableResult"]/tbody/tr[{i + 1}]/td[{j + 5}]/a/img')
                    except NoSuchElementException:
                        try:
                            element = driver.find_element(By.XPATH,
                                                          f'//*[@id="tableResult"]/tbody/tr[{i + 1}]/td[{j + 5}]/a[1]/img')
                        except NoSuchElementException:
                            continue
                alt_value = element.get_attribute('alt')
                if alt_value != '좌석매진':
                    driver.implicitly_wait(5)
                    return element
        driver.implicitly_wait(5)
        return None

    @staticmethod
    def __reservation(driver: webdriver.Chrome, element: WebElement) -> bool:
        element.click()

        # On frame detection
        try:
            driver.switch_to.frame('embeded-modal-traininfo')
            driver.find_element(By.XPATH, '/html/body/div/div[2]/p[3]/a').click()
        except NoSuchFrameException:
            pass
        except UnexpectedAlertPresentException:
            pass

        # On alert detection
        while True:
            try:
                driver.switch_to.alert.accept()
            except NoAlertPresentException:
                break

        driver.switch_to.default_content()

        # If no seats remain
        try:
            driver.find_element(By.XPATH, '//*[@id="contents"]/div[1]/div[2]/div/p[2]/a').click()
            return False
        except NoSuchElementException:
            pass
        return True

    def new_logic(self, process_num: int, search_time: int) -> None:
        self.__process_num = process_num
        driver = webdriver.Chrome()
        self.__login(driver)
        self.__move_url(driver, self.__default_url)
        self.__enter_info(driver, search_time)
        element = None
        while True:
            while True:
                self.__select_ktx(driver)
                element = self.__detect_valid_seat(driver)
                if element is not None:
                    break
            if self.__reservation(driver, element):
                break
            print(f'check - {self.__process_num}')
        print(f'yeah - {self.__process_num}')
        return

    def runner(self):
        process_count = self.__calc_need_process()
        param_list = self.__param_recombinator(process_count)
        pool = multiprocessing.Pool(processes=process_count)
        pool.starmap(self.new_logic, param_list)
        pool.close()
        pool.join()
        return
