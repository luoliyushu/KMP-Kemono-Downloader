from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from bs4 import BeautifulSoup
import traceback
from selenium.common.exceptions import NoSuchElementException


class DynamicContent:
    def __init__(self, page_source, soup, driver, status_code=200):
        """
        初始化动态内容对象

        参数:
        - page_source: 网页源代码
        - soup: BeautifulSoup解析对象
        - driver: Selenium WebDriver对象
        - status_code: HTTP状态码，默认200
        """
        self.text = page_source
        self.soup = soup
        self._driver = driver
        self.status_code = status_code

    def close(self):
        """关闭WebDriver"""
        if self._driver:
            self._driver.quit()


def fetch_dynamic_content(
    url,
    root_selector='div.transition-preload#root',
    target_selector=None,
    timeout=10,
    use_proxy=False,
    proxy_url=None,
    headers=None
):
    """
    使用Selenium动态获取网页内容的函数
    返回DynamicContent对象
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')

    if headers:
        for key, value in headers.items():
            options.add_argument(f'--header={key}:{value}')

    if use_proxy and proxy_url:
        options.add_argument(f'--proxy-server={proxy_url}')

    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    try:
        driver = webdriver.Chrome(
            service=ChromeService("./chromedriver.exe"),
            options=options
        )

        driver.implicitly_wait(timeout)
        driver.get(url)

        # 尝试获取HTTP状态码
        try:
            status_code = driver.execute_script(
                "return document.readyState") == 'complete' and 200 or 500
        except:
            status_code = 500

        if root_selector:
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, root_selector))
                )
            except Exception as wait_error:
                print(f"等待根元素 {root_selector} 超时: {wait_error}")

        if target_selector:
            try:
                driver.find_element(By.CSS_SELECTOR, target_selector)
            except Exception as find_error:
                print(f"未找到目标元素 {target_selector}: {find_error}")

        # 加载评论
        try:
            footer = driver.find_element(By.CSS_SELECTOR, "footer.post__footer")
            if "Loading comments" in footer.text:
                try:
                    WebDriverWait(driver, timeout).until_not(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "footer.post__footer>p"))
                    )
                except Exception as wait_error:
                    print(f"等待评论 {driver.current_url} 超时: {wait_error}")
        except NoSuchElementException:
            pass
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        # with open("./爬取的网页源码.html", "w", encoding="utf-8") as f:
        #     f.write(soup.prettify())

        return DynamicContent(page_source, soup, driver, status_code)

    except Exception as e:
        print(f"获取网页内容时发生错误: {e}")
        print(traceback.format_exc())

        if 'driver' in locals():
            driver.quit()

        return None

# 使用示例
# result = fetch_dynamic_content('https://example.com')
# print(result.text)      # 获取网页源码
# print(result.status_code)  # 获取状态码
# result.close()  # 关闭浏览器
