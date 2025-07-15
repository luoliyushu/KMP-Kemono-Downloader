import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
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
    """自定义重试异常类，用于标记需要重试的操作"""
    pass

def setup_logging():
    """
    设置日志系统，创建两个日志文件：
    1. selenium_时间戳.log - 记录程序运行日志
    2. chrome_时间戳.log - 记录Chrome浏览器的日志
    
    Returns:
        tuple: (logger对象, chrome日志文件路径)
    """
    # 创建logs目录（如果不存在）
    if not os.path.exists('chrome_logs'):
        os.makedirs('chrome_logs')
    
    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'chrome_logs/selenium_{timestamp}.log'
    chrome_log_file = f'chrome_logs/chrome_{timestamp}.log'
    
    # 配置日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    return logging.getLogger(__name__), chrome_log_file

class DynamicContent:
    """
    动态内容容器类，用于存储和管理爬取的网页内容
    """
    def __init__(self, page_source, soup, driver, status_code=200):
        """
        初始化动态内容对象
        
        Args:
            page_source (str): 网页源代码
            soup (BeautifulSoup): BeautifulSoup解析对象
            driver (WebDriver): Selenium WebDriver实例
            status_code (int): HTTP状态码
        """
        self.text = page_source
        self.soup = soup
        self._driver = driver
        self.status_code = status_code

    def close(self):
        """
        安全关闭WebDriver并释放资源
        """
        try:
            if self._driver:
                self._driver.quit()
        except Exception as e:
            logger.error(f"关闭WebDriver时发生错误: {str(e)}")

def retry_operation(max_retries=None, retry_delay=2):
    """
    通用重试装饰器，用于自动重试可能失败的操作
    
    Args:
        max_retries (int): 最大重试次数，None表示使用全局设置
        retry_delay (int): 重试间隔时间（秒）
    
    Returns:
        function: 装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 获取实际的重试次数
            retries = max_retries or kwargs.get('max_retries', 30)
            attempt = 0
            
            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except (TimeoutException, StaleElementReferenceException, RetryException) as e:
                    attempt += 1
                    if attempt == retries:
                        logger.error(f"操作[{func.__name__}]失败，已达到最大重试次数 {retries}: {str(e)}")
                        raise
                    logger.warning(f"操作[{func.__name__}]失败，正在进行第 {attempt} 次重试: {str(e)}")
                    time.sleep(retry_delay)
        return wrapper
    return decorator

class WebDriverManager:
    """
    WebDriver管理器类，负责创建和配置Chrome WebDriver
    """
    @staticmethod
    def create_driver(timeout, chrome_log_file, use_proxy=False, proxy_url=None, headers=None):
        """
        创建并配置Chrome WebDriver实例
        
        Args:
            timeout (int): 超时时间（秒）
            chrome_log_file (str): Chrome日志文件路径
            use_proxy (bool): 是否使用代理
            proxy_url (str): 代理服务器URL
            headers (dict): 自定义请求头
        
        Returns:
            WebDriver: 配置好的Chrome WebDriver实例
        """
        options = webdriver.ChromeOptions()
        
        # 基本配置
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # 日志和通知配置
        options.add_argument('--silent')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-software-rasterizer')
        
        # 设置日志输出到文件
        options.add_argument(f'--enable-logging')
        options.add_argument(f'--log-file={chrome_log_file}')
        
        # 添加自定义请求头
        if headers:
            for key, value in headers.items():
                options.add_argument(f'--header={key}:{value}')

        # 设置代理
        if use_proxy and proxy_url:
            options.add_argument(f'--proxy-server={proxy_url}')

        # 创建Chrome服务
        service = ChromeService(
            executable_path="./chromedriver.exe",
            log_output=chrome_log_file
        )

        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.implicitly_wait(timeout)
            return driver
        except Exception as e:
            logger.error(f"创建WebDriver失败: {str(e)}")
            raise

class PageOperations:
    """
    页面操作类，包含所有与页面交互相关的方法
    """
    @staticmethod
    @retry_operation()
    def load_page(driver, url, **kwargs):
        """加载页面并等待完成"""
        driver.get(url)
        if driver.execute_script("return document.readyState") != 'complete':
            raise RetryException("页面加载未完成")
        return 200

    @staticmethod
    @retry_operation()
    def wait_for_element(driver, selector, timeout, **kwargs):
        """等待指定元素出现"""
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    @staticmethod
    @retry_operation()
    def load_comments(driver, timeout, **kwargs):
        """等待评论加载完成"""
        try:
            footer = driver.find_element(By.CSS_SELECTOR, "footer.post__footer")
            if "Loading comments" in footer.text:
                WebDriverWait(driver, timeout).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "footer.post__footer>p"))
                )
        except NoSuchElementException:
            print("该页面不存在评论区")
        except Exception as e:
            logger.warning(f"等待评论失败，继续执行: {str(e)}")

    @staticmethod
    @retry_operation()
    def get_page_content(driver, **kwargs):
        """获取页面内容"""
        page_source = driver.page_source
        if not page_source or len(page_source) < 100:
            raise RetryException("页面内容获取不完整")
        return page_source

def fetch_dynamic_content(
    url,
    root_selector='div.transition-preload#root',
    target_selector=None,
    timeout=20,  # 默认等待时间20秒
    use_proxy=False,
    proxy_url=None,
    headers=None,
    max_retries=30  # 默认重试30次
):
    """
    获取动态网页内容的主函数
    
    Args:
        url (str): 目标网页URL
        root_selector (str): 根元素的CSS选择器
        target_selector (str): 目标元素的CSS选择器
        timeout (int): 超时时间（秒）
        use_proxy (bool): 是否使用代理
        proxy_url (str): 代理服务器URL
        headers (dict): 自定义请求头
        max_retries (int): 最大重试次数
    
    Returns:
        DynamicContent: 包含页面内容的对象，失败则返回None
    """
    global logger
    logger, chrome_log_file = setup_logging()
    retry_count = max_retries
    retry_delay = 2
    
    while retry_count > 0:
        driver = None
        try:
            logger.info(f"开始获取页面内容: {url}")
            
            # 创建WebDriver
            driver = WebDriverManager.create_driver(
                timeout,
                chrome_log_file,
                use_proxy,
                proxy_url,
                headers
            )
            
            # 加载页面
            status_code = PageOperations.load_page(
                driver, url, max_retries=max_retries
            )
            logger.info("页面加载完成")

            # 等待根元素
            if root_selector:
                try:
                    PageOperations.wait_for_element(
                        driver, root_selector, timeout, max_retries=max_retries
                    )
                    logger.info(f"根元素 {root_selector} 加载完成")
                except Exception as e:
                    logger.warning(f"等待根元素失败，继续执行: {str(e)}")

            # 等待目标元素
            if target_selector:
                try:
                    PageOperations.wait_for_element(
                        driver, target_selector, timeout, max_retries=max_retries
                    )
                    logger.info(f"目标元素 {target_selector} 加载完成")
                except Exception as e:
                    logger.warning(f"等待目标元素失败，继续执行: {str(e)}")

            # 等待评论加载
            try:
                PageOperations.load_comments(
                    driver, timeout, max_retries=max_retries
                )
            except Exception as e:
                logger.warning(f"等待评论失败，继续执行: {str(e)}")

            # 获取页面内容
            page_source = PageOperations.get_page_content(
                driver, max_retries=max_retries
            )
            soup = BeautifulSoup(page_source, 'html.parser')
            logger.info("页面内容解析完成")

            return DynamicContent(page_source, soup, driver, status_code)

        except Exception as e:
            retry_count -= 1
            logger.error(f"发生错误 (剩余重试次数: {retry_count}): {str(e)}")
            logger.debug(f"详细错误信息: {traceback.format_exc()}")
            
            if driver:
                driver.quit()
                
            if retry_count <= 0:
                logger.error("达到最大重试次数，操作失败")
                return None
            
            logger.info(f"等待 {retry_delay} 秒后进行第 {max_retries - retry_count} 次重试...")
            time.sleep(retry_delay)
        finally:
            if driver:
                driver.quit()

# 使用示例
if __name__ == "__main__":
    # 基本使用
    result = fetch_dynamic_content(
        url='https://example.com',
        timeout=20,  # 设置20秒超时
        max_retries=30  # 设置30次重试
    )
    
    if result:
        print(f"状态码: {result.status_code}")
        print("内容长度:", len(result.text))
        result.close()  # 关闭浏览器
    
    # 使用代理的示例
    # result = fetch_dynamic_content(
    #     url='https://example.com',
    #     use_proxy=True,
    #     proxy_url='http://proxy.example.com:8080'
    # )
    
    # 自定义请求头的示例
    # result = fetch_dynamic_content(
    #     url='https://example.com',
    #     headers={
    #         'User-Agent': 'Custom User Agent',
    #         'Accept-Language': 'zh-CN,zh;q=0.9'
    #     }
    # )