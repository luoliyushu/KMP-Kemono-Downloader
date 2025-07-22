import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException
)
from bs4 import BeautifulSoup
import traceback
import os
from datetime import datetime

class RetryException(Exception):
    """自定义重试异常，用于标记需要重试的操作"""
    pass

def setup_logging():
    """
    设置日志系统，生成两个日志文件：
    1. chrome_logs/selenium_时间戳.log  — 记录程序运行日志
    2. chrome_logs/chrome_时间戳.log    — 记录 Chrome 浏览器日志
    
    Returns:
        tuple: (logger 对象, chrome 日志文件路径)
    """
    # 如果 chrome_logs 目录不存在，就创建
    if not os.path.exists('chrome_logs'):
        os.makedirs('chrome_logs')

    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    selenium_log = f'chrome_logs/selenium_{timestamp}.log'
    chrome_log = f'chrome_logs/chrome_{timestamp}.log'

    # 配置 logging，输出到文件和控制台
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(selenium_log, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__), chrome_log

class DynamicContent:
    """
    动态内容容器，封装页面源代码、BeautifulSoup 对象、WebDriver 实例和状态码
    调用 close() 可以安全关闭浏览器，释放资源
    """
    def __init__(self, page_source, soup, driver, status_code=200):
        self.text = page_source
        self.soup = soup
        self._driver = driver
        self.status_code = status_code

    def close(self):
        """
        安全关闭 WebDriver 并释放资源
        """
        try:
            if self._driver:
                self._driver.quit()
        except Exception as e:
            logger.error(f"关闭 WebDriver 时发生错误: {e}")

class WebDriverManager:
    """
    WebDriver 管理器：负责创建并配置 Chrome WebDriver
    """
    @staticmethod
    def create_driver(timeout, chrome_log_file, use_proxy=False, proxy_url=None, headers=None):
        """
        创建并配置 Chrome WebDriver 实例
        
        Args:
            timeout (int): 隐式等待超时时间（秒）
            chrome_log_file (str): Chrome 浏览器日志文件路径
            use_proxy (bool): 是否启用代理
            proxy_url (str): 代理服务器地址
            headers (dict): 自定义请求头
        
        Returns:
            WebDriver: 配置完成的 Chrome WebDriver 实例
        """
        options = webdriver.ChromeOptions()

        # 无头模式、禁用 GPU、沙箱等
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        # 隐藏各种通知、日志
        options.add_argument('--silent')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-software-rasterizer')

        # Chrome 自身日志输出到指定文件
        options.add_argument('--enable-logging')
        options.add_argument(f'--log-file={chrome_log_file}')

        # 自定义头部
        if headers:
            for k, v in headers.items():
                options.add_argument(f'--header={k}:{v}')

        # 代理设置
        if use_proxy and proxy_url:
            options.add_argument(f'--proxy-server={proxy_url}')

        # 创建 ChromeService 实例
        service = ChromeService(
            executable_path="./chromedriver.exe",
            log_output=chrome_log_file
        )

        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.implicitly_wait(timeout)
            return driver
        except Exception as e:
            logger.error(f"创建 WebDriver 失败: {e}")
            raise

class PageOperations:
    """
    页面操作类，封装各种单次执行的 Selenium 操作
    """
    @staticmethod
    def load_page(driver, url):
        """
        加载页面并检查 document.readyState 是否为 'complete'
        
        Args:
            driver (WebDriver): 浏览器实例
            url (str): 目标 URL
        
        Returns:
            int: HTTP 状态码（固定返回 200）
        
        Raises:
            RetryException: 页面未加载完毕时抛出
        """
        driver.get(url)
        state = driver.execute_script("return document.readyState")
        if state != 'complete':
            raise RetryException("页面加载未完成")
        return 200

    @staticmethod
    def wait_for_element(driver, selector, timeout):
        """
        等待指定 CSS 选择器的元素出现
        
        Args:
            driver (WebDriver): 浏览器实例
            selector (str): CSS 选择器
            timeout (int): 最长等待时间（秒）
        
        Returns:
            WebElement: 找到的元素
        
        Raises:
            TimeoutException: 超时未找到元素
        """
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    @staticmethod
    def load_comments(driver, timeout):
        """
        等待评论区加载完成，如果没有评论区则捕获 NoSuchElementException
        
        Args:
            driver (WebDriver): 浏览器实例
            timeout (int): 最长等待时间（秒）
        """
        try:
            footer = driver.find_element(By.CSS_SELECTOR, "footer.post__footer")
            if "Loading comments" in footer.text:
                WebDriverWait(driver, timeout).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "footer.post__footer>p"))
                )
        except NoSuchElementException:
            # 页面无评论区
            print("该页面不存在评论区")
        except Exception as e:
            logger.warning(f"等待评论失败，继续执行: {e}")

    @staticmethod
    def get_page_content(driver):
        """
        获取页面源码，若长度不足认为不完整并抛出异常
        
        Args:
            driver (WebDriver): 浏览器实例
        
        Returns:
            str: 页面 HTML 文本
        
        Raises:
            RetryException: 内容长度不足时抛出
        """
        page_source = driver.page_source
        if not page_source or len(page_source) < 100:
            raise RetryException("页面内容获取不完整")
        return page_source

def fetch_dynamic_content(
    url,
    root_selector='div.transition-preload#root',
    target_selector=None,
    timeout=40,
    use_proxy=False,
    proxy_url=None,
    headers=None,
    max_retries=60
):
    """
    获取动态网页内容的主函数
    
    整体流程一旦任何一步出错或超时，
    将直接从步骤 #2“加载页面”重新开始，
    而不在每个小步骤内单独重试。

    Args:
        url (str): 目标网页 URL
        root_selector (str): 根元素 CSS 选择器
        target_selector (str): 目标元素 CSS 选择器
        timeout (int): 各操作超时时间（秒）
        use_proxy (bool): 是否使用代理
        proxy_url (str): 代理服务器地址
        headers (dict): 自定义请求头
        max_retries (int): 最大整体重试次数

    Returns:
        DynamicContent | None: 成功返回 DynamicContent 对象，失败返回 None
    """
    global logger
    logger, chrome_log_file = setup_logging()
    retry_delay = 2  # 每次重试前的等待时长（秒）

    # 整体重试循环
    for attempt in range(max_retries):
        driver = None
        try:
            logger.info(f"第 {attempt+1} 次尝试抓取页面: {url}")

            # 1. 创建 WebDriver
            driver = WebDriverManager.create_driver(
                timeout, chrome_log_file, use_proxy, proxy_url, headers
            )

            # 2. 加载页面并验证 readyState
            status_code = PageOperations.load_page(driver, url)
            logger.info("页面加载完成")

            # 3. 等待根元素加载（可选）
            if root_selector:
                PageOperations.wait_for_element(driver, root_selector, timeout)
                logger.info(f"根元素 {root_selector} 加载完成")

            # 4. 等待目标元素加载（可选）
            if target_selector:
                PageOperations.wait_for_element(driver, target_selector, timeout)
                logger.info(f"目标元素 {target_selector} 加载完成")

            # 5. 等待评论区加载（若存在）
            PageOperations.load_comments(driver, timeout)
            logger.info("评论加载完成或该页面无评论区")

            # 6. 获取页面内容并校验长度
            page_source = PageOperations.get_page_content(driver)
            logger.info("页面内容获取成功")

            # 7. 解析 HTML 并封装返回
            soup = BeautifulSoup(page_source, 'html.parser')
            logger.info("页面内容解析完成")
            return DynamicContent(page_source, soup, driver, status_code)

        except Exception as e:
            # 捕获任何异常，准备重新从“加载页面”步骤开始
            logger.warning(f"第 {attempt+1} 次尝试失败: {e}")
            logger.debug(traceback.format_exc())

            # 关闭浏览器释放资源
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

            # 如果还有剩余重试机会，就等待后继续
            if attempt < max_retries - 1:
                logger.info(f"等待 {retry_delay} 秒后进行第 {attempt+2} 次重试...")
                time.sleep(retry_delay)
            else:
                logger.error("达到最大重试次数，操作失败，返回 None")
                return None

        finally:
            # 确保在任何情况下都关闭 WebDriver
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

if __name__ == "__main__":
    # ----- 基本使用 -----
    result = fetch_dynamic_content(
        url='https://example.com',
        timeout=20,       # 设置加载和等待超时
        max_retries=30    # 设置最大重试次数
    )

    if result:
        print(f"状态码: {result.status_code}")
        print("内容长度:", len(result.text))
        result.close()    # 关闭并释放资源

    # ----- 使用代理 -----
    # result = fetch_dynamic_content(
    #     url='https://example.com',
    #     use_proxy=True,
    #     proxy_url='http://proxy.example.com:8080'
    # )

    # ----- 自定义请求头 -----
    # result = fetch_dynamic_content(
    #     url='https://example.com',
    #     headers={
    #         'User-Agent': 'Custom User Agent',
    #         'Accept-Language': 'zh-CN,zh;q=0.9'
    #     }
    # )
