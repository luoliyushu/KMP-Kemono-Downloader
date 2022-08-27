from queue import Queue
import shutil
from threading import Lock, Semaphore
import requests
from bs4 import BeautifulSoup, ResultSet
import os
import re
import time
import sys
import cfscrape
from tqdm import tqdm
import logging
import requests.adapters
from datetime import datetime, timezone


import jutils
from Threadpool import tname
from DiscordtoJson import DiscordToJson
from HashTable import HashTable
from HashTable import KVPair
from datetime import timedelta
from Threadpool import ThreadPool
import zipextracter
import alive_progress
from PersistentCounter import PersistentCounter

"""
Simple kemono.party downloader relying on html parsing and download by url
Using multithreading
- URL scraping for non discord services is now multithreaded, explosively decreases web scraping time
- Slightly improved url web scraping efficiency
- Fixed Experimental mode bug where download count started at 1 instead of zero, main thread will exit early and
if there is any download thread that was still active, program will hang up.
- Fixed bug where Pixiv and other non kemono links would lead to infinite retries due to program thinking kemono is trying to rate limit
- Fixed rare data race bug where 2 threads attempt to create a directory with the same name at the same time
- Each thread will now have their own session due to sessions not being thread safe
- Slight program optimizations
- Improved internal documentation and removed some useless/cluttered bits
- Now after a download fails to complete, retries continue from where the download left off
- Fixed rare discord bug where program keeps restarting on url that already contains https://kemono in it
- Max thread count of 20 implemented
- Fixed cases where failed downloads were not being registered even though failures were being written to log
- TODO Separate HTTPS component from KMP class
@author Jeff Chen
@version 0.5.5
@last modified 8/27/2022
"""
HEADERS = {'User-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'}
LOG_PATH = os.path.abspath(".") + "\\logs\\"
LOG_NAME = LOG_PATH + "LOG - " + datetime.now(tz = timezone.utc).strftime('%a %b %d %H-%M-%S %Z %Y') +  ".txt"
LOG_MUTEX = Lock()

class Error(Exception):
    """Base class for other exceptions"""
    pass


class UnknownURLTypeException(Error):
    """Raised when url type cannot be determined"""
    pass


class UnspecifiedDownloadPathException(Error):
    """Raised when download path is not given"""
    pass

class DeadThreadPoolException(Error):
    """Raised when download threads are nonexistant or dead"""
    pass


class KMP:
    """
    Kemono.party downloader class, contains everything needed to download
    all of Kemono parties resources
    """
    __folder: str               # Folder to download files to
    __unzip: bool               # Unzipping flag
    __tcount: int               # Thread count
    __chunksz: int              # Size of chunks to download in
    __threads:ThreadPool        # Threadpool with tcount threads
    __sessions:list             # requests sessions for threads
    __session:requests.Session  # request session for main thread
    __unpacked:bool             # Unpacked download type flag
    __http_codes:list[int]      # list of HTTP codes to retry on
    __CONTAINER_PREFIX = "https://kemono.party" # Prefix of kemono website
    __register:HashTable            # Registers a directory, combats multiple posts using the same name
    __register_mutex:Lock           # Lock for the register
    __fcount:int                    # Number of downloaded files
    __fcount_mutex:Lock             # Mutex for fcount 
    __failed:int                    # Number of downloaded files
    __failed_mutex:Lock             # Mutex for fcount     
    __post_name_exclusion:list[str] # Keywords in excluded posts
    __link_name_exclusion:list[str] # Keywords in excluded posts
    __ext_blacklist:HashTable       # Stores excluded extensions
    __timeout:int                   # Timeout for network issues
    __post_process:list             # Directories that require post processing when they contain text only
    __download_server_name_type:bool    # Switch to use server hashed names instead of custom names
    __progress:Semaphore                # Semaphore for progress bar, one release means 1 file downloaded
    __progress_mutex:Lock               # Mutex for semaphore
    __dir_lock:Lock                     # Mutex for when a directory is being created

    def __init__(self, folder: str, unzip:bool, tcount: int | None, chunksz: int | None, ext_blacklist:list[str]|None = None , timeout:int = -1, http_codes:list[int] = None, post_name_exclusion:list[str]=[], download_server_name_type:bool = False,\
        link_name_exclusion:list[str] = []) -> None:
        """
        Initializes all variables. Does not run the program

        Param:
            folder: Folder to download to, cannot be None
            unzip: True to automatically unzip files, false to not
            tcount: Number of threads to use, max thread count is 12, default is 6
            chunksz: Download chunk size, default is 1024 * 1024 * 64
            ext_blacklist: List of file extensions to skips, does not contain '.' and no spaces
            timeout: Max retries, default is infinite (-1)
            http_codes: Codes to retry downloads for 
            post_name_exclusion: keywords in excluded posts, must be all lowercase to be case insensitive
            download_server_name_type: True to download server file name, false to use a program defined naming scheme instead
            link_name_exclusion: keyword in excluded link. The link is the plaintext, not the link pointer, must be all lowercase to be case insensitive.
        """
        tname.id = None
        if folder:
            self.__folder = folder
        else:
            raise UnspecifiedDownloadPathException
        self.__dir_lock = Lock()
        self.__progress_mutex = Lock()
        self.__progress = Semaphore(value=0)
        self.__register = HashTable(1000)
        self.__fcount = 0
        self.__unzip = unzip
        self.__fcount_mutex = Lock()
        self.__timeout = timeout
        self.__failed = 0
        self.__failed_mutex = Lock()
        self.__post_process = []
        self.__post_name_exclusion = post_name_exclusion
        self.__download_server_name_type = download_server_name_type
        self.__link_name_exclusion = link_name_exclusion
        self.__register_mutex = Lock()
        
        if not http_codes or len(http_codes) == 0:
            self.__http_codes = [429, 403]
        else:
            self.__http_codes = http_codes
        
        if not tcount or tcount <= 0:
            self.__tcount = 6
        else:
            self.__tcount = min(20, tcount)

        if chunksz and chunksz > 0 and chunksz <= 12:
            self.__chunksz = chunksz
        else:
            self.__chunksz = 1024 * 1024 * 64
        
        self.__unpacked = 0
        
        if ext_blacklist:
            self.__ext_blacklist = HashTable(len(ext_blacklist) * 2)
            for ext in ext_blacklist:
                self.__ext_blacklist.hashtable_add(KVPair(ext, ext))
        else:
            self.__ext_blacklist = None
        # Create session ###########################
        self.__sessions = []
        for _ in range(0, max(self.__tcount, self.__tcount)):
            session = cfscrape.create_scraper(requests.Session())
            adapter = requests.adapters.HTTPAdapter(pool_connections=self.__tcount, pool_maxsize=self.__tcount, max_retries=0, pool_block=True)
            session.mount('http://', adapter)
            self.__sessions.append(session)
        self.__session = cfscrape.create_scraper(requests.Session())
        adapter = requests.adapters.HTTPAdapter(pool_connections=self.__tcount, pool_maxsize=self.__tcount, max_retries=0, pool_block=True)
        self.__session.mount('http://', adapter)
        
    def reset(self) -> None:
        """
        Resets register and download count, should be called if the KMP
        object will be reused; otherwise, downloaded url data will persist
        and file download and failed count will persist.
        """
        self. __register = HashTable(10)
        self.__fcount = 0
        self.__failed = 0

    def close(self) -> None:
        """
        Closes KMP download session, cannot be reopened, must be called to prevent
        unclosed socket warnings 
        """
        [session.close() for session in self.__sessions]
        self.__session.close()

    def __download_file(self, src: str, fname: str, display_bar:bool = True) -> None:
        """
        Downloads file at src. Skips if 
            (1) a file already exists sharing the same fname and size 
            (2) Contains blacklisted extensions
            (3) Has been downloaded already with this KMP instance
        Param:
            src: src of image to download
            fname: what to name the file to download, with extensions. Absolute path
            display_bar: Whether to display download progress bar or not. If False, display bar is not displayed and self.__progress 
                    is incremented instead.
        Pre: If program is called with a thread, it will use a unique session, if called by main, it will use a newly
            generated session that is closed before function terminates
        """
        close = False
        # Configure tname and session #######################################################################################################
        if not tname.name:
            tname.name = "default thread name" 
            session = cfscrape.create_scraper(requests.Session())
            adapter = requests.adapters.HTTPAdapter(pool_connections=self.__tcount, pool_maxsize=self.__tcount, max_retries=0, pool_block=True)
            session.mount('http://', adapter)
            close = True 
        else:
            session = self.__sessions[tname.id]   
        
        logging.debug("Downloading " + fname + " from " + src)
        r = None
        timeout = 0
        
        # Grabbing content length  ###########################################################################################################
        while not r:
            try:
                r = session.request('HEAD', src, timeout=5)

                if r.status_code >= 400:
                    if r.status_code in self.__http_codes and 'kemono' in src:
                        if timeout == self.__timeout:
                            logging.critical("Reached maximum timeout, writing error to log")
                            jutils.write_to_file(LOG_NAME, "429 TIMEOUT -> SRC: {src}, FNAME: {fname}\n".format(src=src, fname=fname), LOG_MUTEX)
                            self.__failed_mutex.acquire()
                            self.__failed += 1
                            self.__failed_mutex.release()
                            if not display_bar:
                                self.__progress_mutex.acquire()
                                self.__progress.release()
                                self.__progress_mutex.release()
                            return
                        else:
                            timeout += 1
                            logging.warning("Kemono party is rate limiting this download, download restarted in 10 seconds:\nCode: " + str(r.status_code) + "\nSrc: " + src + "\nFname: " + fname)
                            time.sleep(10)
                        
                    else:
                        logging.critical("(" + str(r.status_code) + ")" + "Link provided cannot be downloaded from, likely a dead link. Check HTTP code and src: \nSrc: " + src + "\nFname: " + fname)
                        jutils.write_to_file(LOG_NAME, "{code} TIMEOUT -> SRC: {src}, FNAME: {fname}\n".format(code=str(r.status_code), src=src, fname=fname), LOG_MUTEX)
                        self.__failed_mutex.acquire()
                        self.__failed += 1
                        self.__failed_mutex.release()
                        if not display_bar:
                            self.__progress_mutex.acquire()
                            self.__progress.release()
                            self.__progress_mutex.release()
                        return

            except(requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                logging.debug("Connection request unanswered, retrying -> URL: {url}".format(url=src))
        fullsize = r.headers.get('Content-Length')

        f = fname.split('\\')[len(fname.split('\\')) - 1]   # File name only, used for bar display

        # If file does not have a length, it is most likely an invalid file
        if fullsize == None:
            logging.critical("Download was attempted on an undownloadable file, details describe\nSrc: " + src + "\nFname: " + fname)
            jutils.write_to_file(LOG_NAME, "UNDOWNLOADABLE -> SRC: {src}, FNAME: {fname}\n".format(code=str(r.status_code), src=src, fname=fname), LOG_MUTEX)
            self.__failed_mutex.acquire()
            self.__failed += 1
            self.__failed_mutex.release()
        
        # Download and skip duplicate file
        elif (not os.path.exists(fname) or os.stat(fname).st_size != int(fullsize)) and (not self.__ext_blacklist or self.__ext_blacklist.hashtable_exist_by_key(f.partition('.')[2]) == -1): 
            headers = HEADERS
            mode = 'wb'
            done = False
            downloaded = 0          # Used for updating the bar
            while(not done):
                try:
                    # Get the session
                    data = None
                    while not data:
                        try:
                            data = session.get(src, stream=True, timeout=5, headers=headers)
                        except(requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                             logging.debug("Connection timeout on {url}".format(url=src))
                            
                    # Download the file with visual bars 
                    if display_bar:
                        
                        with open(fname, mode) as fd, tqdm(
                                desc=fname,
                                total=int(fullsize) - downloaded,
                                unit='iB',
                                unit_scale=True,
                                leave=False,
                                bar_format= tname.name + ": (" + str(self.__threads.get_qsize()) + ")->" + f + '[{bar}{r_bar}]',
                                unit_divisor=int(1024)) as bar:
                            for chunk in data.iter_content(chunk_size=self.__chunksz):
                                sz = fd.write(chunk)
                                fd.flush()
                                bar.update(sz)
                                downloaded += sz
                            time.sleep(1)
                            bar.clear()
                    else:
                        with open(fname, 'wb') as fd:
                            for chunk in data.iter_content(chunk_size=self.__chunksz):
                                sz = fd.write(chunk)
                                fd.flush()
                                downloaded += sz
                            time.sleep(1)

                    # Checks if the file is correctly downloaded, if so, we are done
                    if(os.stat(fname).st_size == int(fullsize)):
                        done = True
                        logging.debug("Downloaded Size (" + fname + ") -> " + fullsize)
                        # Increment file download count, file is downloaded at this point
                        self.__fcount_mutex.acquire()
                        self.__fcount += 1
                        self.__fcount_mutex.release()
                    else:
                        logging.warning("File not downloaded correctly, will be restarted!\nSrc: " + src + "\nFname: " + fname)
                        headers = {'User-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
                                  'Range': 'bytes=' + str(downloaded) + '-' + fullsize}
                        mode = 'ab'
                except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError):
                    logging.debug("Chunked encoding error has occured, server has likely disconnected, download has restarted")
                except FileNotFoundError:
                    logging.debug("Cannot be downloaded, file likely a link, not a file ->" + fname)
                    done = True



            # Unzip file if specified
            if self.__unzip and zipextracter.supported_zip_type(fname):
                p = fname.rpartition('\\')[0] + "\\" + re.sub(r'[^\w\-_\. ]|[\.]$', '',
                                          fname.rpartition('\\')[2]).rpartition(" by")[0] + "\\"
                self.__dir_lock.acquire()
                if not os.path.exists(p):
                    os.mkdir(p)
                self.__dir_lock.release()
                zipextracter.extract_zip(fname, p, temp=True)
        
        # Increment progress mutex
        if not display_bar:
            self.__progress_mutex.acquire()
            self.__progress.release()
            self.__progress_mutex.release()
        
        # Closes session if session was created within this function
        if close:
            session.close()

    def __trim_fname(self, fname: str) -> str:
        """
        Trims fname, returns result. Extensions are kept:
        For example
        
        When ext length of ?<filename>.ext token is <= 6:
        "/data/2f/33/2f33425e67b99de681eb7638ef2c7ca133d7377641cff1c14ba4c4f133b9f4d6.txt?f=File.txt"
        -> File.txt

        Or

        When ext length of ?<filename>.ext token is > 6:
        "/data/2f/33/2f33425e67b99de681eb7638ef2c7ca133d7377641cff1c14ba4c4f133b9f4d6.jpg?f=File.jpe%3Ftoken-time%3D1570752000..."
        ->2f33425e67b99de681eb7638ef2c7ca133d7377641cff1c14ba4c4f133b9f4d6.jpg

        Or

        When ' ' exists
        'Download まとめDL用.zip'
        -> まとめDL用.zip

        Param: 
            fname: file name
        Pre: fname follows above conventions
        Return: trimmed filename with extension
        """
        # Case 3, space
        case3 = fname.partition(' ')[2]
        if case3 != fname and len(case3) > 0:
            return re.sub(r'[^\w\-_\. ]|[\.]$', '',
                                          case3)

        case1 = fname.rpartition('=')[2]
        # Case 2, bad extension provided
        if len(case1.rpartition('.')[2]) > 6:
            first = fname.rpartition('?')[0]
            return re.sub(r'[^\w\-_\. ]|[\.]$', '',
                                          first.rpartition('/')[2])
        
        # Case 1, good extension
        return re.sub(r'[^\w\-_\. ]|[\.]$', '',
                                          case1)

    def __queue_download_files(self, imgLinks: ResultSet, dir: str, base_name:str | None, task_list:Queue|None, counter:PersistentCounter) -> Queue:
        """
        Puts all urls in imgLinks in threadpool download queue. If task_list is not None, then
        all urls will be added to task_list instead of being added to download queue.

        Param:
        imgLinks: all image links within a Kemono container
        dir: where to save the images
        base_name: Prefix to name files, None for just a counter
        task_list: list to store tasks into instead of directly processing them, None to directly process them
        counter: a counter to increment for each file and used to rename files
        
        Raise: DeadThreadPoolException when no download threads are available, ignored if enqueue is false
        Return modified tasklist, is None if task_list param is None
        """

        if not self.__threads.get_status():
            raise DeadThreadPoolException
        
        if not base_name:
            base_name = ""

        for link in imgLinks:
            href = link.get('href')
            # Type 1 image - Image in Files section
            if href:
                src = self.__CONTAINER_PREFIX + href
            # Type 2 image - Image in Content section
            else:
                
                target = link.get('src')
               # Polluted link check, Fanbox is notorious for this
                if "downloads.fanbox" not in target:
                     # Hosted on non KMP server
                    if 'http' in target:
                        src = target
                    # Hosted on KMP server
                    else:
                        src = self.__CONTAINER_PREFIX + target
                else:
                    src = None
            # If a src is detected, it is added to the download queue/task list    
            if src:
                logging.debug("Extracted content link: " + src)
                
                # Select the correct download name based on switch
                if self.__download_server_name_type:
                    fname = dir + base_name + self.__trim_fname(src)
                else:
                    fname = dir + base_name + str(counter.get()) + '.' + self.__trim_fname(src).rpartition('.')[2]

                # Check if the post attachment shares the same name as another post attachemnt
                # Adjust filename if found
                self.__register_mutex.acquire()
                value = self.__register.hashtable_lookup_value(fname)
                if value != None:  # If register, update titleDir and increment value
                    self.__register.hashtable_edit_value(fname, value + 1)
                    split = fname.partition('.')
                    fname = split[0] + "(" + str(value) + ")." + split[2]
                else:   # If not registered, add to register at value 1
                    self.__register.hashtable_add(KVPair[str, int](fname, 1))
                self.__register_mutex.release()
                    
                if not task_list:
                    self.__threads.enqueue((self.__download_file, (src, fname)))
                else:
                    task_list.put((self.__download_file, (src, fname, False)))
                counter.toggle()
        return task_list

    def __download_file_text(self, textLinks:ResultSet, dir:str) -> None:
        """
        Scrapes all text and their links in textLink and saves it to 
        in dir

        Param:
            textLink: Set of links and their text in Files segment
            dir: Where to save the text and links to. Must be a .txt file
        """
        frontOffset = 5
        endOffset = 4
        currOffset = 0
        listSz = len(textLinks)
        strBuilder = []
        # No work to be done if the file already exists
        if os.path.exists(dir) or listSz <= 9:
            return
        
        # Record data
        for txtlink in textLinks:
            if frontOffset > 0:
                frontOffset -= 1
            elif(endOffset < listSz - currOffset):
                text = txtlink.get('href').strip()
                if not text.isnumeric():
                    strBuilder.append(txtlink.text.strip() + '\n')
                    strBuilder.append(text + '\n')
                    strBuilder.append("____________________________________________________________\n")
            currOffset += 1
        
        # Write to file if data exists
        if len(strBuilder) > 0:
            jutils.write_utf8("".join(strBuilder), dir, 'w')


            

    def __process_container(self, url: str, root: str, task_list:Queue|None) -> Queue:
        """
        Processes a kemono container which is the page used to store post content

        Supports
        - downloading all visable images
        - content divider (BUG other urls are included)
        - download divider

        Param:
        url: url of the container
        root: directory to store the content
        task_list: List to store tasks in instead of processing them immediately, None to process tasks immediately
        
        Pre: If program is called with a thread, it will use a unique session, if called by main, it will use a newly
                generated session that is closed before function terminates
        
        Return: task_list after modification
        Raise: DeadThreadPoolException when no download threads are available, ignored if get_list is true
        """
        
        logging.debug("Processing: " + url + " to be stored in " + root)
        counter = PersistentCounter()     # Counter to name the images as 
        if not self.__threads.get_status():
            raise DeadThreadPoolException
        
        close = False
        # Determine which session to use
        if not tname.id:
            close = True
            session = cfscrape.create_scraper(requests.Session())
            adapter = requests.adapters.HTTPAdapter(pool_connections=self.__tcount, pool_maxsize=self.__tcount, max_retries=0, pool_block=True)
            session.mount('http://', adapter)
            close = True
        else:
            session = self.__sessions[tname.id]    
        
        # Get HTML request and parse the HTML for image links and title ############
        reqs = None
        while not reqs:
            try:
                reqs = self.__session.get(url, timeout=5, headers=HEADERS)
            except(requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                 logging.debug("Connection timeout")
        soup = BeautifulSoup(reqs.text, 'html.parser')
        while "500 Internal Server Error" in soup.find("title"):
            logging.error("500 Server error encountered at " +
                          url + ", retrying...")
            time.sleep(2)
            reqs = None
            while not reqs:
                try:
                    reqs = self.__session.get(url, timeout=5, headers=HEADERS)
                except(requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                    logging.debug("Connection timeout")
            soup = BeautifulSoup(reqs.text, 'html.parser')
        imgLinks = soup.find_all("a", {'class':'fileThumb'})
        

        # Create a new directory if packed or use artist directory for unpacked
        work_name =  (re.sub(r'[^\w\-_\. ]|[\.]$', '', soup.find("title").text.strip())
             ).split("\\")[0]
        backup = work_name + " - "
        
        # Check if a post is excluded
        for keyword in self.__post_name_exclusion:
            if keyword in work_name.lower():
                logging.debug("Excluding {post}, kword: {kword}".format(post=work_name, kword=keyword) )
                
                # Close session if applicable
                if close:
                    session.close()
                return
        
        # If not unpacked, need to consider if an existing dir exists
        if self.__unpacked < 2:
            titleDir = os.path.join(root, \
            work_name) + "\\"
            work_name = ""
            
            # Check if directory has been registered ###################################
            self.__register_mutex.acquire()
            value = self.__register.hashtable_lookup_value(titleDir)
            if value != None:  # If register, update titleDir and increment value
                self.__register.hashtable_edit_value(titleDir, value + 1)
                titleDir = titleDir[:len(titleDir) - 1] + "(" + str(value) + ")\\"
            else:   # If not registered, add to register at value 1
                self.__register.hashtable_add(KVPair[str, int](titleDir, 1))
            self.__register_mutex.release()
        # For unpacked, all files will be placed in the artist directory
        else:
            titleDir = root
            work_name += ' - '


        # Create directory if not registered
        if not os.path.isdir(titleDir):
            os.makedirs(titleDir)
        reqs.close()

        # Download all 'files' #####################################################
        # Image type
        
        self.__queue_download_files(imgLinks, titleDir, work_name, task_list, counter)
        
        
        # Link type
        self.__download_file_text(soup.find_all('a', {'target':'_blank'}), titleDir + work_name + "file__text.txt")

        # Scrape post content ######################################################
        content = soup.find("div", class_="post__content")

        if content:
            if(os.path.exists(titleDir + work_name + "post__content.txt")):
                logging.debug("Skipping duplicate post_content download")
            else:
                text = content.getText(separator='\n', strip=True)
                if len(text) > 0:
                    # Text section
                    with open(titleDir + work_name + "post__content.txt", "w", encoding="utf-8") as fd:
                        fd.write(text)
                        links = content.find_all("a")
                        for link in links:
                            hr = link.get('href')
                            if not hr:
                                logging.info("Href returns None at url: {u}".format(u=url))
                            else:
                                fd.write("\n" + hr)
                
            # Image Section
            task_list = self.__queue_download_files(content.find_all('img'), titleDir, work_name, task_list, counter)

        # Download post attachments ##############################################
        attachments = soup.find_all("a", class_="post__attachment-link")
        if attachments:
            for attachment in attachments:
                download = attachment.get('href')
                # Confirm that attachment not from patreon 
                if 'patreon' not in download:
                    src = self.__CONTAINER_PREFIX + download
                    aname =  self.__trim_fname(attachment.text.strip())
                    # If src does not contain excluded keywords, download it
                    if not self.__exclusion_check(self.__link_name_exclusion, aname):
                        fname = os.path.join(titleDir, work_name + aname)
                        
                        # Check if the post attachment shares the same name as another post attachemnt
                        # Adjust filename if found
                        self.__register_mutex.acquire()
                        value = self.__register.hashtable_lookup_value(fname)
                        if value != None:  # If register, update titleDir and increment value
                            self.__register.hashtable_edit_value(fname, value + 1)
                            split = fname.partition('.')
                            fname = split[0] + "(" + str(value) + ")." + split[2]
                        else:   # If not registered, add to register at value 1
                            self.__register.hashtable_add(KVPair[str, int](fname, 1))
                        self.__register_mutex.release()
                        
                        if task_list:
                            task_list.put((self.__download_file, (src, fname, False)))
                        else:
                            self.__threads.enqueue((self.__download_file, (src, fname)))
        
        

        # Download post comments ################################################
        if(os.path.exists(titleDir + work_name + "post__comments.txt")):
                logging.debug("Skipping duplicate post comments")
        elif "patreon" in url or "fanbox" in url:
            comments = soup.find("div", class_="post__comments")
            if comments and len(comments.getText(strip=True)) > 0:
                text = comments.getText(separator='\n', strip=True)
                if(text and text != "No comments found for this post." and len(text) > 0):
                    jutils.write_utf8(comments.getText(separator='\n', strip=True), titleDir + work_name + "post__comments.txt", 'w')
        
        # Add to post process queue if partial unpack is on
        if self.__unpacked == 1:
            self.__post_process.append((self.__partial_unpack_post_process, (titleDir, root + backup)))
        
        # Close session if applicable
        if close:
            session.close()
        
        return task_list
    
    def __exclusion_check(self, tokens:list[str], target:str)->bool:
        """
        Checks if target contains an excluded token

        Args:
            tokens (list[str]): _description_
            target (str): _description_
        Returns: True if contians excluded keywords, false if does not
        """
        target = target.lower()
        # check if src contains excluded keywords
        for kword in tokens:
            if kword in target:
                logging.debug("Excluding {post}, kword: {kword}".format(post=target, kword=kword))
                return True
        return False
    
    def __partial_unpack_post_process(self, src, dest)->None:
        """
        Checks if a folder in src is text only, if so, move everything 
        from src to dest

        Param:
            src: folder to check
            dest: folder to move to
        """
        # Examine each file in src
        for f in os.listdir(src):
            # When encounter first non text file, return from func
            if f.rpartition('.')[2] != "txt":
                return

        # If not returned, move everything and delete old folder
        for f in os.listdir(src):
            shutil.move(src + f, dest + f)
        shutil.rmtree(src)    
        return

    def __process_window(self, url: str, continuous: bool, get_list:bool=False, pool:ThreadPool|None=None) -> Queue:
        """
        Processes a single main artist window, a window is a page where multiple artist works can be seen

        Param: 
            url: url of the main artist window
            continuous: True to attempt to visit next pages of content, False to not
            get_list: Return a list of tasks instead of processing the data immediately
            pool: None for single thread or an initialized pool for multithreading
        Return: If get_list is true, a list of tasks needed to process the data is returned.
        Post: pool may not have completed all of its tasks 
        """
        
        reqs = None
        task_list:Queue = None
        
        if get_list:
            task_list = Queue(0)
        # Make a connection
        while not reqs:
            try:
                reqs = self.__session.get(url, timeout=5, headers=HEADERS)
            except(requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                 logging.debug("Connection timeout")
        soup = BeautifulSoup(reqs.text, 'html.parser')
        reqs.close()
        # Create directory
        artist = soup.find("meta", attrs={'name': 'artist_name'})
        titleDir = self.__folder + re.sub(r'[^\w\-_\. ]|[\.]$', '',
                                          artist.get('content')) + "\\"
        if not os.path.isdir(titleDir):
            os.makedirs(titleDir)

        contLinks = soup.find_all("div", class_="post-card__link")
        suffix = "?o="
        counter = 0

        # Process each window
        while contLinks:
            # Process all links on page
            for link in contLinks:
                content = link.find("a")
                pool.enqueue((self.__process_container, (self.__CONTAINER_PREFIX + content.get('href'), titleDir, task_list,)))
            if continuous:
                # Move to next window
                counter += 25
                reqs = None
                while not reqs:
                    try:
                        reqs = self.__session.get(url + suffix + str(counter), timeout=5, headers=HEADERS)
                    except(requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                         logging.debug("Connection timeout")
                soup = BeautifulSoup(reqs.text, 'html.parser')
                reqs.close()
                contLinks = soup.find_all("div", class_="post-card__link")
            else:
                contLinks = None

        return task_list


    def __download_discord_js(self, jsList:dict, titleDir:str, get_list:bool) -> list[str] | tuple:
        """
        Downloads any file found in js and returns text data

        Param:
            jsList: Kemono discord server json to download
            titleDir: Where to save data
        Pre: text_file does not have data from previous runs. Data is appended so old data
                will persist.
        Pre: titleDir exists
        Return: Buffer containing text data, if get_list is true, return a tuple where text data is
                    [0] and download data is [1]
        """
        imageDir = titleDir + "images\\"
        counter = 0
        task_list = None
        if get_list:
            task_list = []
        # make dir
        self.__dir_lock.acquire()
        if not os.path.isdir(imageDir):
            os.mkdir(imageDir)
        self.__dir_lock.release()
        stringBuilder = []
        # Process each json individually
        for jsCluster in reversed(jsList):
            for js in reversed(jsCluster): # Results became a list within a list due to multiprocessing update
                # Add buffer
                stringBuilder.append('_____________________________________________________\n')

                # Process name 
                stringBuilder.append(js.get('author').get('username'))
                stringBuilder.append('\t')

                # Process date
                stringBuilder.append(js.get('published'))
                stringBuilder.append('\n')

                # Process content
                stringBuilder.append(js.get('content'))
                stringBuilder.append('\n')

                # Process embeds
                for e in js.get('embeds'):

                    if e.get('type') == "link":
                        try:
                            if e.get('title'):
                                stringBuilder.append(e.get('title') + " -> " + e.get('url') + '\n')
                            elif e.get('description'):
                                stringBuilder.append(e.get('description') + " -> " + e.get('url') + '\n')
                            else:
                                stringBuilder.append(e.get('url') + '\n')
                        except TypeError:
                            logging.critical("Unidentified edge case in Discord JS scraping process has occured, details:\
                                {info}".format(info=e))

                # Add attachments
                for i in js.get('attachments'):
                    if "https" != i.get('path')[0:5]:
                        url = self.__CONTAINER_PREFIX + i.get('path')
                    else:
                        url = i.get('path')
                    stringBuilder.append(url + '\n\n')
                    
                    # Check if the attachment is dupe
                    value = self.__register.hashtable_lookup_value(url)
                    if value == None:   # If not registered, add to register at value 1
                        self.__register.hashtable_add(KVPair[str, int](url, 1))
                    
                        # Download the attachment
                        if get_list:
                            task_list.append((self.__download_file, (url, imageDir + str(counter) + '.' + url.rpartition('.')[2], False)))
                        else:
                            self.__threads.enqueue((self.__download_file, (url, imageDir + str(counter) + '.' + url.rpartition('.')[2])))
                        counter += 1
                    # If is on the register, do not download the attachment

        # Write to file
        return stringBuilder if(not get_list) else (stringBuilder, task_list,)

    def __process_discord_server(self, serverJs:dict, titleDir:str, get_list:bool) -> list|None:
        """
        Process a discord server

        Param:
            serverJS: discord server json token, in format {"id":xxx,"name":xxx}
            titleDir: Where to store discord content, absolute directory ends with '\\'
        """
        dir = titleDir + serverJs.get('name') + '\\'
        # Make sure a dupe directory does not exists, if so, adjust dir name
        value = self.__register.hashtable_lookup_value(dir)
        if value != None:  # If register, update titleDir and increment value
            self.__register.hashtable_edit_value(dir, value + 1)
            dir = dir[0:len(dir) - 1] + "(" + str(value) + ")\\"
        else:   # If not registered, add to register at value 1
            self.__register.hashtable_add(KVPair[str, int](dir, 1))

        text_file = "discord__content.txt"
        # makedir
        self.__dir_lock.acquire()
        if not os.path.isdir(dir):
            os.mkdir(dir)
        # clear data   
        elif os.path.exists(dir + text_file):
            os.remove(dir + text_file)
        self.__dir_lock.release()
        # Read every json on the server and put it in queue
        discordScraper = DiscordToJson()
        js = discordScraper.discord_lookup_all(serverJs.get("id"), threads=self.__tcount, sessions=self.__sessions)
        
        data = self.__download_discord_js(js, dir, get_list=get_list)
        toReturn = None
        # Write buffered discord text content to file
        if get_list:
            buffer = ("".join(data[0]))
            jutils.write_utf8("".join(buffer), dir + 'discord__content.txt', 'a')
            toReturn = data[1]
        else:
            jutils.write_utf8("".join(data), dir + 'discord__content.txt', 'a')
        return toReturn


    def __process_discord(self, url:str, titleDir:str, get_list:bool=False) -> list|None:
        """ 
        Process discord kemono links using multithreading

        Param:
            url: discord url
            titleDir: directory to store discord content
        """
        discordScraper = DiscordToJson()
        dir = titleDir

        # Makedir
        if not os.path.isdir(dir):
            os.makedirs(dir)

        # Get server ID(s)
        servers = discordScraper.discord_lookup(url.rpartition('/')[2], self.__session)
        
        if len(servers) == 0:
            return
        
        task_queue = None
        if get_list:
            task_queue = Queue(0)
            
        # Process each server
        for s in servers:
            # Process server
            task_list = self.__process_discord_server(s, dir, get_list=get_list)
            if get_list:
                for task in task_list:
                    task_queue.put(task)
        
        return task_queue
                
    # TODO custom threadpool instead of automatically created one
    def __call_and_interpret_url(self, url: str, get_list:bool=False) -> Queue|None:
        """
        Calls a function based on url type
        https://kemono.party/fanbox/user/xxxx -> process_window()
        https://kemono.party/fanbox/user/xxxx?o=xx -> process_window() one page only
        https://kemono.party/fanbox/user/xxxx/post/xxxx -> process_container()
        https://kemono.party/discord/server/xxxx -> process_discord()

        Anything else -> UnknownURLTypeException

        Param:
            url: url to process
            get_list: True to return a queue of task instead of directly processing the url's download
        Return: Queue of tasks, None if task_list is false
        Raise:
            UnknownURLTypeException when url type cannot be determined
        """
        if get_list:
            task_list = Queue(0)
        else:
            task_list = None
        scrape_pool = ThreadPool(self.__tcount)
        scrape_pool.start_threads()
        # For single window page, we can process it directly since we don't have to flip to next pages
        if '?' in url:
            task_list = self.__process_window(url, False, get_list=get_list, pool=scrape_pool)
        # Single artist work requires a directory similar to one if it were a window to be created, once done, it can be processed
        elif "post" in url:
            # Build directory
            reqs = None
            while not reqs:
                try:
                    reqs = self.__session.get(url, timeout=5, headers=HEADERS)
                except(requests.exceptions.ConnectionError ,requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                     logging.debug("Connection timeout")
            if(reqs.status_code >= 400):
                logging.error("Status code " + str(reqs.status_code))
            soup = BeautifulSoup(reqs.text, 'html.parser')
            artist = soup.find("a", attrs={'class': 'post__user-name'})
            titleDir = self.__folder + \
                re.sub(r'[^\w\-_\. ]|[\.]$', '', artist.text.strip()) + "\\"
            if not os.path.isdir(titleDir):
                os.makedirs(titleDir)
            reqs.close()
            # Process container
            self.__process_container(url, titleDir, task_list)

        # Discord requires a totally different method compared to other services as we are making API calls instead of scraping HTML
        elif 'discord' in url:
            task_list = self.__process_discord(url, self.__folder + url.rpartition('/')[2] + "\\", get_list=get_list)


        # For multiple window pages
        elif 'user' in url:
            task_list = self.__process_window(url, True, get_list=get_list, pool=scrape_pool)
        # Not found, we complain
        else:
            logging.critical("Unknown URL -> " + url)
            # WRITETOLOG
            raise UnknownURLTypeException
        
        if not task_list and get_list:
            logging.critical("Failed")
            logging.critical(url)
            exit(-1)
        
        scrape_pool.join_queue()
        scrape_pool.kill_threads()
        return task_list

    def __create_threads(self, count: int) -> ThreadPool:
        """
        Creates count number of downThreads and starts it

        Param:
            count: how many threads to create
        Return: Threads
        """
        threads = ThreadPool(count)
        threads.start_threads()
        return threads

    def __kill_threads(self, threads: ThreadPool) -> None:
        """
        Kills all threads in threads. Deadlocked or infinitely running threads cannot be killed using
        this function.

        Threads are killed after the download queue is finished

        Param:
        threads: threads to kill
        """
        threads.join_queue()
        threads.kill_threads()

    def monitor_queue(self, q:Queue, resp:str|None=None):
        """
        Block until q is joined, displays resp afterwards 

        Args:
            q (Queue): q to block until joined
        """
        q.join()
        if resp:
            logging.info(resp)
    
    def __prog_bar(self, max:int):
        """
        Display a progress bar, will be thread will be locked until max
        """
        counter = 0
        with alive_progress.alive_bar(max, title='Files Downloaded:') as bar:
            while(counter < max):
                # Acquire progress sem
                self.__progress.acquire()
                
                # Increment counter
                counter += 1
                bar()
    
    def alt_routine(self, url: str | list[str] | None, unpacked:int | None, benchmark:bool = False) -> None:
        """
        Basically the same as routine but uses an experimental routine to be used in a future development
        
        Main routine, processes an 3 kinds of artist links specified in the project spec.
        if url is None, ask for a url.

        Param:
        url: supported url(s), if single string, process single url, if list, process multiple
            urls. If None, ask user for a url
        unpacked: Whether or not to pack contents tightly or loosely, default is tightly packed.
            Levels 0 -> no unpacking, 1 -> partial unpacking, 2 -> unpack all
        benchmark: True to download content, false to stop after scraping content
        """
        if unpacked is None:
            self.__unpacked = 0
        else:
            self.__unpacked = unpacked


        # Generate threads #########################
        self.__threads = self.__create_threads(self.__tcount)

        # Keeps a list of download tasks Queues, each entry is a Queue!
        queue_list:list = []
        
        # Get url to download ######################
        # List type url
        if isinstance(url, list):
            for line in url:
                line = line.strip()
                if len(line) > 0:
                    logging.info("Fetching {url}".format(url=line))
                    queue_list.append(self.__call_and_interpret_url(line, get_list=True))

        # User input url
        else:
            while not url or "https://kemono.party" not in url:
                url = input("Input a url, or type 'quit' to exit> ")

                if(url == 'quit'):
                    self.__kill_threads(self.__threads)
                    return
            logging.info("Fetching, {url}".format(url=url))
            queue_list.append(self.__call_and_interpret_url(url, get_list=True))
        
        
        # Process the task_list
        sz = 0
        for task_list in queue_list:
            sz += task_list.qsize()
        logging.info("Number of files to be downloaded -> {fnum}".format(fnum=str(sz)))
        
        # If benchmarking is selecting, test ends here
        if benchmark:
            logging.info("Benchmark has been completed!")
            return
        
        # Create a threadpool to keep track of which artist works are completed.
        task_threads = ThreadPool(6)
        task_threads.start_threads()
        if isinstance(url, str):
            task_list = queue_list[0]
            task_threads.enqueue((self.monitor_queue, (task_list, "{url} is completed".format(url=url),)))
            self.__threads.enqueue_queue(task_list=task_list)
        else:    
            for i, task_list in enumerate(queue_list):
                task_threads.enqueue((self.monitor_queue, (task_list, "{url} is completed".format(url=url[i]),)))
                self.__threads.enqueue_queue(task_list=task_list)
        
        self.__prog_bar(sz)
        # Wait for task_list is joined
        for task_list in queue_list:
            task_list.join()
        # Wait for queue
        self.__threads.join_queue()
        task_threads.join_queue()
        
        # Start post processing
        for f in self.__post_process:
            self.__threads.enqueue(f)
        self.__post_process = []
        
        # Close threads ###########################
        self.__kill_threads(self.__threads)
        self.__kill_threads(task_threads)
        logging.info("Files downloaded: " + str(self.__fcount))
        if self.__failed > 0:
            logging.info("Failed: {failed}, stored in {log}".format(failed=self.__failed, log=LOG_NAME))
    
    
    def routine(self, url: str | list[str] | None, unpacked:int | None) -> None:
        """
        Main routine, processes an 3 kinds of artist links specified in the project spec.
        if url is None, ask for a url.

        Param:
        url: supported url(s), if single string, process single url, if list, process multiple
            urls. If None, ask user for a url
        unpacked: Whether or not to pack contents tightly or loosely, default is tightly packed.
            Levels 0 -> no unpacking, 1 -> partial unpacking, 2 -> unpack all
        
        """
        if unpacked is None:
            self.__unpacked = 0
        else:
            self.__unpacked = unpacked


        # Generate threads #########################
        self.__threads = self.__create_threads(self.__tcount)

        # Get url to download ######################
        # List type url
        if isinstance(url, list):
            for line in url:
                line = line.strip()
                if len(line) > 0:
                    self.__call_and_interpret_url(line)

        # User input url
        else:
            while not url or "https://kemono.party" not in url:
                url = input("Input a url, or type 'quit' to exit> ")

                if(url == 'quit'):
                    self.__kill_threads(self.__threads)
                    return

            self.__call_and_interpret_url(url)
        
        # Wait for queue
        self.__threads.join_queue()

        # Start post processing
        for f in self.__post_process:
            self.__threads.enqueue(f)
        self.__post_process = []

        # Close threads ###########################
        self.__kill_threads(self.__threads)
        logging.info("Files downloaded: " + str(self.__fcount))
        if self.__failed > 0:
            logging.info("Failed: {failed}, stored in {log}".format(failed=self.__failed, log=LOG_NAME))


def help() -> None:
    """
    Displays help information on invocating this program
    """    
    logging.info("DOWNLOAD CONFIG - How files are downloaded\n\
        -f <textfile.txt> : Bulk download from text file containing links\n\
        -d <path> : REQUIRED - Set download path for single instance, must use '\\'\n\
        -c <#> : Adjust download chunk size in bytes (Default is 64M)\n\
        -t <#> : Change download thread count (default is 6)\n")
        
    
    logging.info("EXCLUSION - Exclusion of specific downloads\n\
        -x \"txt, zip, ..., png\" : Exclude files with listed extensions, NO '.'s\n\
        -p \"keyword1, keyword2,...\" : Keyword in excluded posts, not case sensitive\n\
        -l \"keyword1, keyword2,...\" : Keyword in excluded link, not case sensitive. Is for link plaintext, not its target\n")
    
    logging.info("DOWNLOAD FILE STRUCTURE - How to organize downloads\n\
        -s : If a artist work is text only, do not create a dedicated directory for it, partially unpacks files\n\
        -u : Enable unpacked file organization, all works will not have their own folder, overrides partial unpack\n\
        -e : Download server name instead of program defined naming scheme\n\
        -v : Enables unzipping of files automatically\n")
    
    logging.info("TROUBLESHOOTING - Solutions to possible issues\n\
        -z \"500, 502,...\" : HTTP codes to retry downloads on, default is 429 and 403\n\
        -r <#> : Maximum number of HTTP code retries, default is infinite\n\
        -h : Help\n\
        --EXPERIMENTAL : Enable experimental mode\n\
        --BENCHMARK : Benchmark experiemental mode's scraping speed, does not download anything\n")

def main() -> None:
    """
    Program runner
    """
    #logging.basicConfig(level=logging.DEBUG)
    start_time = time.monotonic()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

    # logging.basicConfig(level=logging.DEBUG, filename='log.txt', filemode='w')
    folder = False
    urls = False
    unzip = False
    tcount = -1
    chunksz = -1
    unpacked = False
    excluded:list = []
    retries = -1
    partial_unpack = False
    http_codes = []
    post_excluded = []
    server_name = False
    link_excluded = []
    experimental = False
    benchmark = False
    if len(sys.argv) > 1:
        pointer = 1
        while(len(sys.argv) > pointer):
            if sys.argv[pointer] == '-f' and len(sys.argv) >= pointer:
                with open(sys.argv[pointer + 1], "r") as fd:
                    urls = fd.readlines()
                pointer += 2
            elif sys.argv[pointer] == '-v':
                unzip = True
                pointer += 1
                logging.info("UNZIP -> " + str(unzip))
            elif sys.argv[pointer] == '--EXPERIMENTAL':
                experimental = True
                pointer += 1
                logging.info("EXPERIMENTAL -> " + str(experimental))
            elif sys.argv[pointer] == '-e':
                server_name = True
                pointer += 1
                logging.info("SERVER_NAME_DOWNLOAD -> " + str(server_name))                
            elif sys.argv[pointer] == '-u':
                unpacked = True
                partial_unpack = False
                pointer += 1
                logging.info("UNPACKED -> TRUE")
            elif sys.argv[pointer] == '--BENCHMARK':
                benchmark = True
                pointer += 1
                logging.info("BENCHMARK -> TRUE")
            elif sys.argv[pointer] == '-d' and len(sys.argv) >= pointer:
                folder = os.path.abspath(sys.argv[pointer + 1])

                if folder[len(folder) - 1] == '\"':
                    folder = folder[:len(folder) - 1] + '\\'
                elif not folder[len(folder) - 1] == '\\':
                    folder += '\\'

                logging.info("FOLDER -> " + folder)
                if not os.path.exists(folder):
                    logging.critical("FOLDER Path does not exist, terminating program!!!")
                    return
                pointer += 2
            elif sys.argv[pointer] == '-t' and len(sys.argv) >= pointer:
                tcount = int(sys.argv[pointer + 1])
                pointer += 2
                logging.info("DOWNLOAD_THREAD_COUNT -> " + str(tcount))
            elif sys.argv[pointer] == '-c' and len(sys.argv) >= pointer:
                chunksz = int(sys.argv[pointer + 1])
                pointer += 2
                logging.info("CHUNKSZ -> " + str(chunksz))
            elif sys.argv[pointer] == '-r' and len(sys.argv) >= pointer:
                retries = int(sys.argv[pointer + 1])
                pointer += 2
                logging.info("RETRIES -> " + str(retries))
            elif sys.argv[pointer] == '-x' and len(sys.argv) >= pointer:
                 
                for ext in sys.argv[pointer + 1].split(','):
                    excluded.append(ext.strip().lower())
                pointer += 2
                logging.info("EXCLUDED -> " + str(excluded))
            elif sys.argv[pointer] == '-l' and len(sys.argv) >= pointer:
                 
                for ext in sys.argv[pointer + 1].split(','):
                    link_excluded.append(ext.strip().lower())
                pointer += 2
                logging.info("LINK_EXCLUDED -> " + str(link_excluded))
            elif sys.argv[pointer] == '-p' and len(sys.argv) >= pointer:
                 
                for ext in sys.argv[pointer + 1].split(','):
                    post_excluded.append(ext.strip().lower())
                pointer += 2
                logging.info("EXCLUDED POST KEYWORDS -> " + str(post_excluded))
            
            elif sys.argv[pointer] == '-z' and len(sys.argv) >= pointer:
                
                for ext in sys.argv[pointer + 1].split(','):
                    http_codes.append(int(ext.strip()))
                pointer += 2
                logging.info("HTTP CODES -> " + str(http_codes))
            elif sys.argv[pointer] == '-s':
                if not unpacked:
                    partial_unpack = True
                    logging.info("PARTIAL_UNPACK -> TRUE")
                    pointer += 1
            else:
                pointer = len(sys.argv)

    # Prelim dirs
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)

    # Run the downloader
    if folder:
        downloader = KMP(folder, unzip, tcount, chunksz, ext_blacklist=excluded, timeout=retries, http_codes=http_codes, post_name_exclusion=post_excluded, download_server_name_type=server_name, link_name_exclusion=link_excluded)
        
        if experimental or benchmark:
            if unpacked:
                downloader.alt_routine(urls, 2, benchmark)
            elif partial_unpack:
                downloader.alt_routine(urls, 1, benchmark)
            else:
                downloader.alt_routine(urls, 0, benchmark)
        else:
            if unpacked:
                downloader.routine(urls, 2)
            elif partial_unpack:
                downloader.routine(urls, 1)
            else:
                downloader.routine(urls, 0)
        downloader.close()
    else:
        help()

    # Report time
    end_time = time.monotonic()
    logging.info(timedelta(seconds=end_time - start_time))


if __name__ == "__main__":
    main()