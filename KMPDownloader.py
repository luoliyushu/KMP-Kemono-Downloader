from queue import Queue
import shutil
import sqlite3
from threading import Lock, Semaphore
import traceback
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
#import webbrowser
from ssl import SSLError
import threading


from Threadpool import tname
from DiscordtoJson import DiscordToJson
from HashTable import HashTable
from HashTable import KVPair
from datetime import timedelta
from Threadpool import ThreadPool
import zipextracter
import alive_progress
from PersistentCounter import PersistentCounter
import jutils
from DB import DB

from fetch_dynamic import fetch_dynamic_content



"""
Simple kemono.party downloader relying on html parsing and download by url
Using multithreading
@author Jeff Chen
@version 0.6.2.3
@last modified 9/10/2023
"""
request_headers = {
    "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
}                                                                                            # Headers to be used for python requests, modified later on since is constantly changing
LOG_PATH = os.path.abspath(".") + "\\logs\\"                                                                    # Directory for logging
LOG_NAME = LOG_PATH + "LOG - " + datetime.now(tz = timezone.utc).strftime('%a %b %d %H-%M-%S %Z %Y') +  ".txt"  # Name for log file to use
LOG_MUTEX = Lock()                                                                                              # Mutex for log file
download_format_types = ["image", "audio", "video", "plain", "stream", "application", "7z", "audio"]            # Download types for file attachments, can be modified by the user with switches

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
    __container_prefix:str      # Prefix of kemono website
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
    __wait:float                        # Wait time between downloads in seconds
    __db:DB                             # Name of database
    __update:bool                       # True for update mode, false for download mode
    __exclcomments:bool                 # Exclude comments switch
    __exclcontents:bool                 # Exclude contents switch 
    __minsize:bool                      # Minimum downloadable file size
    __existing_file_register:HashTable  # Existing files and their size
    __existing_file_register_lock:Lock  # Lock for existing file table
    __predupe:bool                      # True to prepend () in cases of dupe, false to postpend ()
    __urls:list[str]                    # List of downloaded artist urls
    __latest_urls:list[str]             # List of downloaded artist's latest urls
    __override_paths:list[str]           # List of file paths to override old file paths if they exists in db
    __config:tuple                      # Download configuration
    __artist:list[str]                  # Downloaded artist name
    __reupdate:bool                     # True to reupdate, false to not
    __date:bool                         # True to append date to files/folder, false to not
    __id:bool                           # True to prepend id to files/folder, false to not
    __rename:bool                      # True to rename tracked artist files (nothing is downloaded), false for regular operation.
    __tempextr:bool                     # True to extract to temp folder then move to dir, false to extract within dir only
    __root:str                          # Root directory
    __scount:int                        # Number of files skipped
    __scount_mutex:Lock                 # lock for scount
    __connection_timeout:int            # Timeout used for general connection issues
    #__wait_browser_cond:threading.Condition  # Conditional used for blocking when waiting on CAPTCHA to be completed
    #__browser_active:bool               # True if browser for captcha has been open, false if not
    #__browser_active_mutex:Lock         # Mutex used for browser_active
     
    def __init__(self, folder: str, unzip:bool, tcount: int | None, chunksz: int | None, ext_blacklist:list[str]|None = None , timeout:int = 30, http_codes:list[int] = None, post_name_exclusion:list[str]=[], download_server_name_type:bool = False,\
        link_name_exclusion:list[str] = [], wait:float = 0, db_name:str = "KMP.db", track:bool = False, update:bool = False, exclcomments:bool = False, exclcontents:bool = False, minsize:float = 0, predupe:bool = False, prefix:str = "https://kemono.party", 
        disableprescan:bool = False, date:bool = False, id:bool = False, rename:bool = False, tempextr:bool = True, root:str = os.path.dirname(os.path.realpath(__file__)), connect_timeout:int = 10, **kwargs) -> None:
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
            wait: time in seconds to wait in between downloads.
            db_name: database name, this object creates or extends upon 2 tables named Parent & Child
            track: true to add entries to database, false otherwise
            update: Routines update instead of downloading artists
            predupe: True to prepend () in cases of dupe, false to postpend ()
            prefix: Prefix of kemono URL. Must include https and any other relevant parts of the URL and does not end in slash.
            disableprescan: True to disable prescan used to build temp dupe file database.
            date: True to use date info for file names, False to not
            id: True to use id info for file names, False to not
            rename: True to rename and/or delete local files if a online version was found during archiving. NOTE: makes sure directory looks identical to online copy
            tempextr: True to extract to a temp directory then move to dest directory, false to extract to the dest directory
            root: Root directory for files, default is where KMPDownloader.py is located
            connect_timeout: Timeout in seconds when a general connectivity error has occured.
            kwargs: not in use for now
        """
        self.__connection_timeout = connect_timeout
        #self.__wait_browser_cond = threading.Condition()
        #self.__browser_active = Lock()
        self.__root = root
        tname.id = None
        if folder:
            self.__folder = folder
        elif not update and not kwargs["reupdate"]:
            raise UnspecifiedDownloadPathException
        self.__scount = 0
        self.__scount_mutex = Lock()
        self.__dir_lock = Lock()
        self.__progress_mutex = Lock()
        self.__progress = Semaphore(value=0)
        self.__register = HashTable(10)
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
        self.__db = DB(os.path.join(root, db_name))
        self.__update = update
        self.__exclcomments = exclcomments
        self.__exclcontents = exclcontents
        self.__urls = []    
        self.__latest_urls = []     
        self.__override_paths = []         
        self.__config = locals() 
        self.__artist = []       
        self.__container_prefix = prefix
        self.__date = date
        self.__tempextr = tempextr
        self.__id = id
        if minsize < 0:
            self.__minsize = 0
        else:
            self.__minsize = minsize
        
        if not http_codes or len(http_codes) == 0:
            self.__http_codes = [429, 403, 502]
        else:
            self.__http_codes = http_codes
        
        if not tcount or tcount <= 0:
            self.__tcount = 1
        else:
            self.__tcount = min(5, tcount)
            
        if wait < 2:
            self.__wait = 2
        else:
            self.__wait = wait

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
        self.__reupdate = kwargs["reupdate"]
        self.__rename = rename
        # Create database  #############
        if track or update or kwargs["reupdate"]:
            # Check if database exists
            if os.path.exists(os.path.join(self.__root, db_name)):
                # If exists, create a backup
                if(not os.path.exists(os.path.join(self.__root, "Data_Backup"))):
                    os.makedirs(os.path.join(self.__root, "Data_Backup"))
                # Copy db file to backup location
                db_part_name = db_name.rpartition('.')
                shutil.copyfile(os.path.join(self.__root, db_name), os.path.join(self.__root, "Data_Backup/", db_part_name[0] + "-" + datetime.now(tz = timezone.utc).strftime('%a %b %d %H-%M-%S %Z %Y') + "." + db_part_name[2])) 
                
            
            # Create a new table
            self.__db.executeNCommit("CREATE TABLE IF NOT EXISTS Parent2 (url TEXT, artist TEXT, type TEXT, latest TEXT, destination TEXT, config TEXT)")
             
            # Update older databases
            legacy_table:sqlite3.Cursor = self.__db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Parent'").fetchall()
            
            if (len(legacy_table) == 1):
                cursor = self.__db.execute("SELECT * from Parent")
                col_names = [description[0] for description in cursor.description]
                
                # Version 6.0's db
                if len(col_names) == 4:
                    # Get all column data
                    urls = [item[0] for item in self.__db.execute("SELECT url FROM Parent").fetchall()]
                    latest = [item[0] for item in self.__db.execute("SELECT latest FROM Parent").fetchall()]
                    dfolder = [item[0] for item in self.__db.execute("SELECT destination FROM Parent").fetchall()]
                    
                    # Add to the new table
                    for i in range(0, len(urls)):
                        self.__db.execute(("INSERT INTO Parent2 VALUES (?, ?, 'Kemono', ?, ?, ?)", (urls[i], None, latest[i], dfolder[i], None),))
                        
                    # Remove old table
                    self.__db.executeNCommit("DROP TABLE Parent")
           
        else:
            self.__db = None
        
        # Create session ###########################
        self.__sessions = []
        for _ in range(0, max(self.__tcount, self.__tcount)):
            session = cfscrape.create_scraper(requests.Session())
            session.max_redirects = 5
            adapter = requests.adapters.HTTPAdapter(pool_connections=self.__tcount, pool_maxsize=self.__tcount, max_retries=0, pool_block=True)
            session.mount('http://', adapter)
            self.__sessions.append(session)
        self.__session = cfscrape.create_scraper(requests.Session())
        self.__session.max_redirects = 5
        adapter = requests.adapters.HTTPAdapter(pool_connections=self.__tcount, pool_maxsize=self.__tcount, max_retries=0, pool_block=True)
        self.__session.mount('http://', adapter)
        
        # TODO choose better number
        self.__existing_file_register = HashTable(10000000)
        self.__existing_file_register_lock = Lock()
        
        # File prescan
        if not disableprescan:
            # If update is selected, read in all update paths
            if update or kwargs["reupdate"]:
                # Use a set to skip ignore duplicate paths
                update_path_set = {item[0] for item in self.__db.execute("SELECT destination FROM Parent2").fetchall()}
                for path in update_path_set:
                    self.__fregister_preload(path, self.__existing_file_register, self.__existing_file_register_lock)

            # If update is not selected, read from download folder
            else:
                self.__fregister_preload(folder, self.__existing_file_register, self.__existing_file_register_lock)
            logging.info("Finished scanning directory")
        
        self.__predupe = predupe        
    
        
    def __fregister_preload(self, dir:str, fregister:HashTable, mutex:Lock) -> None:
        """
        Registers all files and directories within a path to a Hashtable with multithreading

        Args:
            path (str): Directory path to walk
            fregister (HashTable): If provided, appends to the hashtable
            mutex (Lock): Mutex to be used with fregister
        Pre: path ends with '/' and uses '/'
        Returns:
            HashTable: Hashtable with all file records if register is None
        """
        # If path does not exists, skip
        logging.info(f"Please wait, scanning {dir}")
        
        if not os.path.exists(dir):
            logging.warning("{} does not exists, preload skipped".format(dir))
            return None
        
        
        # Pull up current directory information
        contents = os.scandir(dir)
        
        # Generate thread pool
        file_pool = ThreadPool(100)
        file_pool.start_threads()
                    
        # Iterate through all elements
        for file in contents:
            # If is a directory, recursive call into directory and append result
            if file.is_dir():
                file_pool.enqueue((self.__fregister_preload_helper, (file_pool, file.path + '\\', fregister, mutex,)))

            # TODO sort values by radix sort and implement binary search

        file_pool.join_queue()
        file_pool.kill_threads()
    
    def __basename_generator(self, name:str)->tuple:
        """
        Given a file or dir name (not path), return a basename

        Args:
            name (str): name of a file or directory

        Returns:
            tuple (str): Size 1 or 2 tuple. Size 1 has basename of file while size 2 has basename
                        in first position and an alternate basename in second position if it is impossible
                        to derive just one basename from a name.
        """
        basename = name
        ext = name.rpartition('.')[2]
        
        # Predupe case
        if name[0] == "(":
            basename = name.rpartition(") ")[2]
        # Postdupe case
        else:
            # 2 types of '(' checked for since previous versions <=0.6 don't have spacing between filename and () 
            if ' (' in name:
                basename = name.partition(" (")[0] + (("." + ext) if ext != name else "")
            elif '(' in name:
                basename = name.partition("(")[0] + ext
            # Probably unecessary trim but to be safe
            basename = basename.strip()
                        
        basename_tokens = basename.split(" ")        
        secondpath = None
        if len(basename_tokens) >= 3: # Skips files with inadequent tokens
            # Date case
            if basename_tokens[len(basename_tokens) - (3 if ext != name else 1)].isnumeric():
                # Check if new keyword is used for date
                if basename_tokens[len(basename_tokens) - (5 if ext != name else 3)] == "Published":
                    basename = " ".join(basename_tokens[0:len(basename_tokens) - (5 if ext != name else 3)]) + ((" " + " ".join(basename_tokens[len(basename_tokens) - 2:]) if ext != name else ""))
                # If no keyword is used for date
                else:
                    basename = " ".join(basename_tokens[0:len(basename_tokens) - (4 if ext != name else 2)]) + ((" " + " ".join(basename_tokens[len(basename_tokens) - 2:]) if ext != name else ""))
            
            # ID Case
            basename_tokens = basename.split(" ")
            if basename_tokens[0].isnumeric(): 
                secondpath = basename   # Is impossible to know if first token references id or something else
                basename = (" ".join(basename_tokens[1:]))
        
        
        return (basename, secondpath) if secondpath else (basename,)
    
    def __fregister_preload_helper(self, pool:ThreadPool, dir:str, fregister:HashTable, mutex:Lock) -> None:
        """
        Helper function for __fregister_preload. Performs the operation of assigning thread task and recursively
        visiting each directory and registering each file. 
        
        Data registered to fregtister in the following format:
        
        KVPair(base_name, [file1_name, file1_identifier, file2_name, file2_identifier...])
        Where basename is the key which should be used when searching the hash table and the array
        contains the values where each even position is the actual filename and odd position is the
        file's unique identifier which includes file size, file content, and etc.
        
        Note that there may be multiple basenames for a single file depending on the format of the file
        and the format of its parent directory.
        
        Args:
            path (str): Workers to be used for the registering of files and folders
            dir (str): directory to have the worker threads examine
            fregister (HashTable): Table to register data to
            mutex (Lock): Mutex for fregister
        Pre: path ends with '/' and uses '/'
        Returns:
            HashTable: Hashtable with all file records if register is None
        """

        # Pull up current directory information
        contents = os.scandir(dir)
        
        # Iterate through all elements
        for file in contents:
            
            # If is a directory, recursive call into directory and append result
            if file.is_dir():
                pool.enqueue((self.__fregister_preload_helper, (pool, file.path + '\\', fregister, mutex,)))
            # If not directory, get file size and remove any ()
            elif file.stat().st_size > 0:
                # Get directory name by itself 
                dir_partition = os.path.dirname(dir).rpartition("\\")
                dir_name = dir_partition[2]
                
                # Generate basename of dir_name
                base_dir_names = self.__basename_generator(dir_name)
                # Generate basename of file
                base_file_names = self.__basename_generator(file.name)
                
                # Get file size
                fsize = os.stat(file.path).st_size
                
                # Recreate fullpath
                dir_paths = [os.path.join(dir_partition[0], n) for n in base_dir_names] # Reconstruct dirpath
                file_paths = []
                for dir_path in dir_paths:
                    for base_file_name in base_file_names:
                        file_paths.append(os.path.join(dir_path, base_file_name))
                
                for fullpath in file_paths:  
                    # Check if is text file and is a file written by the program (contains __)
                    if(file.name.endswith("txt") and "__" in file.name):
                        # Add file contents to register
                        try:
                            with open(file.path, 'r', encoding="utf-") as fd:
                                # Text content of file
                                contents = fd.read()
                                
                                mutex.acquire()
                                # fullpath
                                data = fregister.hashtable_lookup_value(fullpath)
                                # If entry does not exists, add it               
                                if not data:
                                    fregister.hashtable_add(KVPair(fullpath, [hash(contents), file.path]))
                                    
                                # Else append data to currently existing entry if not already included in the entry
                                elif(file.path not in data):
                                    data.append(hash(contents))
                                    data.append(file.path)
                                    fregister.hashtable_edit_value(fullpath, data)      
                                mutex.release()
                        except(UnicodeDecodeError):
                            logging.warning("UnicodeDecodeError in {}, skipping file".format(file.path))
                            #os.remove(file.path)
                        except Exception as e:
                            logging.error("Handled an unknown exception, skipping file: {}".format(e.__class__.__name__))
                    else:    
                        # Add size value to register
                        mutex.acquire()
                        data = fregister.hashtable_lookup_value(fullpath)
                        # If entry does not exists, add it           
                        if not data:
                            fregister.hashtable_add(KVPair(fullpath, [fsize, file.path]))
                        # Else append data to currently existing entry
                        elif(file.path not in data):
                            data.append(fsize)
                            data.append(file.path)
                            fregister.hashtable_edit_value(fullpath, data)
                        mutex.release()
            # TODO sort values by radix sort and implement binary search
        
    def reset(self) -> None:
        """
        Resets register and download count, should be called if the KMP
        object will be reused; otherwise, downloaded url data will persist
        and file download and failed count will persist.
        TODO DEPRECATED, needs to be updated
        """
        self. __register = HashTable(10)
        self.__fcount = 0
        self.__failed = 0

    def close(self) -> None:
        """
        Closes KMP download session, cannot be reopened, must be called to prevent
        unclosed socket warnings. Database is processed and closed here as well.
        """
        [session.close() for session in self.__sessions]
        self.__session.close()
        
        # Update db
        if self.__db:
            done = False
            while not done:
                try:
                    for i in range(0, len(self.__urls)):
                        # Check if db entry already exists
                        entry = self.__db.execute(("SELECT * FROM Parent2 WHERE url LIKE '%'||?", (self.__urls[i].rpartition(".")[2].partition('/')[2],),))
                        old_config = None
                        entries = entry.fetchall()
                        # If it already exists, remove the entry
                        if len(entries) > 0:
                            # Save any old data 
                            old_config = entries[0][5]
                            # Remove old entry
                            self.__db.execute(("DELETE FROM Parent2 WHERE url LIKE '%'||?", (self.__urls[i].rpartition(".")[2].partition('/')[2],),))
                        # Insert updated entry
                        self.__db.execute(("INSERT INTO Parent2 VALUES (?, ?, 'Kemono', ?, ?, ?)", (self.__urls[i], self.__artist[i], self.__latest_urls[i], self.__override_paths[i], str(self.__config) if not old_config else old_config),))
                    done = True
                except sqlite3.OperationalError:
                    
                    logging.warning("Database is locked, waiting 10s before trying again".format(self.__db))
                    time.sleep(10)
        
            self.__db.commit()
            self.__db.close()

    def __submit_failure(self, msg:str|None) -> None:
        """
        Called when a file related failure occurs
        
        Param:
            msg: Message to write to LOG_NAME, skip step if None
        """
        jutils.write_to_file(LOG_NAME, msg, LOG_MUTEX) if msg else None
        self.__failed_mutex.acquire()
        self.__failed += 1
        self.__failed_mutex.release()
    
    def __submit_progress(self) -> None:
        """
        Called when progress is made on files
        """
        self.__progress_mutex.acquire()
        self.__progress.release()
        self.__progress_mutex.release()
    
    def __submit_downloaded(self) -> None:
        """
        Called when a file is successfully downloaded
        """
        self.__fcount_mutex.acquire()
        self.__fcount += 1
        self.__fcount_mutex.release()
    
    def __submit_skipped(self)->None:
        """
        Called when a file download is skipped
        """
        self.__scount_mutex.acquire()
        self.__scount += 1
        self.__scount_mutex.release()
        
    def __download_file(self, src: str, fname: str, org_fname: str, display_bar:bool = True) -> None:
        """
        Downloads file at src. Skips if 
            (1) a file already exists sharing the same fname and size 
            (2) Contains blacklisted extensions
            (3) File's name and size matches a locally downloaded file
        However, if self.__rename is true, file will be renamed according to self's vars if src file matches a local copy
        Param:
            src: src of image to download
            fname: what to name the file to download, with extensions. Absolute path
            org_fname: fname but the base version of it. Used for file name collision checks.
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
            session.max_redirects = 5
            adapter = requests.adapters.HTTPAdapter(pool_connections=self.__tcount, pool_maxsize=self.__tcount, max_retries=0, pool_block=True)
            session.mount('http://', adapter)
            close = True 
        else:
            session = self.__sessions[tname.id]   
        
        logging.debug("Downloading " + fname + " from " + src)
        r = None
        timeout = 0
        notifcation = 0
        
        # Grabbing content length  ###########################################################################################################
        while not r:
            try:
                r = session.request('HEAD', src, timeout=10)
                if r.status_code >= 400:
                    if r.status_code in self.__http_codes and 'kemono' in src:
                        if timeout == self.__timeout:
                            logging.critical("Reached maximum timeout, writing error to log")
                            self.__submit_failure("TIMEOUT -> SRC: {src}, FNAME: {fname}\n".format(src=src, fname=fname))
                            if not display_bar:
                                self.__submit_progress()
                            return
                        else:
                            timeout += 1
                            logging.warning(f"Kemono party is rate limiting this download, download restarted in {self.__connection_timeout} seconds:\nCode: " + str(r.status_code) + "\nSrc: " + src + "\nFname: " + fname)
                            time.sleep(self.__connection_timeout)
                        
                    else:
                        logging.critical("(" + str(r.status_code) + ")" + "Link provided cannot be downloaded from, likely a dead link. Check HTTP code and src: \nSrc: " + src + "\nFname: " + fname)
                        self.__submit_failure("{code} UNREGISTERED TIMEOUT AND NONKEMONO LINK -> SRC: {src}, FNAME: {fname}\n".format(code=str(r.status_code), src=src, fname=fname))
                        if not display_bar:
                            self.__submit_progress()
                        return
            except requests.exceptions.Timeout:
                logging.warning("Connection timed out, this may be due to CAPTCHA, please open Kemono and solve the captcha, program will sleep for 20 seconds")
                time.sleep(20)
            except(requests.exceptions.RequestException) as e:
                logging.warning(f"{e.__class__.__name__} has occured for {src} ({notifcation}), thread sleeping for {self.__connection_timeout} seconds.")
                
                notifcation+=1
                time.sleep(self.__connection_timeout)
                
                if(notifcation % 10 == 0):
                    logging.warning("Connection has been retried multiple times on {url} for {f}, if problem persists, check https://status.kemono.party/".format(url=src, f=fname))
                
                logging.debug("Connection request unanswered, retrying -> URL: {url}, FNAME: {f}".format(url=src, f=fname))
        
        # Checking if file has a correct download format
        format = r.headers["content-type"]
        found = False
        for f in download_format_types:
            if f in format:
                found = True
                break
        
        if not found:
            logging.warning("{} has nontracked MIME type {}, skipping".format(src, format))
            if not display_bar:
                self.__submit_progress()
            return
            
        
        fullsize = r.headers.get('Content-Length')

        f = fname.split('\\')[len(fname.split('\\')) - 1]   # File name only, used for bar display

        # If file does not have a length, it is most likely an invalid file
        if fullsize == None:
            logging.critical("Download was attempted on an undownloadable file, details describe\nSrc: " + src + "\nFname: " + fname)
            self.__submit_failure("UNDOWNLOADABLE -> SRC: {src}, FNAME: {fname}\n".format(code=str(r.status_code), src=src, fname=fname))
        else:
            # Convert fullsize
            fullsize = int(fullsize)
            
            # Check to see if file exists in the file register
            self.__existing_file_register_lock.acquire()
            
            if self.__existing_file_register.hashtable_exist_by_key(org_fname) == -1:
                # If does not exists, add an entry
                self.__existing_file_register.hashtable_add(KVPair(org_fname, []))
            
            
            # Check 3 conditions when renaming
            download = self.__dupe_file_procedure(fname, org_fname, fullsize, True)
                
            # Otherwise, download files that are greater than minimum size and whose extension is not blacklisted
            if download and fullsize > self.__minsize and (not self.__ext_blacklist or self.__ext_blacklist.hashtable_exist_by_key(f.partition('.')[2]) == -1): 
                headers = request_headers
                mode = 'wb'
                done = False
                downloaded = 0          # Used for updating the bar
                failed = False
                
                # Make a new file name according to number of matching fname entries
                download_fname = fname
                
                # Make sure that file does not already exists
                i = 0
                while(os.path.exists(download_fname)):
                    # Starts at 0 due to backward compatibility with previous dupe naming scheme
                    # predupe case
                    if self.__predupe:
                        ftokens = fname.rpartition('\\')
                        download_fname = ftokens[0] + "\\(" + str(i) + ") " + ftokens[2]
                    # postdupe case
                    else:
                        ftokens = fname.rpartition('.')     
                        download_fname = ftokens[0] + " (" + str(i) + ")." + ftokens[2]
                    i += 1
                    
                self.__existing_file_register_lock.release()
                
                while(not done):
                    try:
                        # Get the session
                        data = None
                        while not data:
                            try:
                                data = session.get(src, stream=True, timeout=10, headers=headers)
                            except requests.exceptions.Timeout:
                                logging.warning("Connection timed out, this may be due to CAPTCHA, please open Kemono and solve the captcha, program will sleep for 20 seconds")
                                time.sleep(20)      
                            except(requests.exceptions.RequestException) as e:
                                logging.warning(f"{e.__class__.__name__} has occured for {src}, thread sleeping for {self.__connection_timeout} seconds.")
                                
                                time.sleep(self.__connection_timeout)
                                
                        # Download the file with visual bars 
                        if display_bar:
                            
                            with open(download_fname, mode) as fd, tqdm(
                                    desc=download_fname,
                                    total=fullsize - downloaded,
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
                                time.sleep(self.__wait)
                                bar.clear()
                        else:
                            with open(download_fname, 'wb') as fd:
                                
                                try:
                                    for chunk in data.iter_content(chunk_size=self.__chunksz):
                                        if chunk:
                                            sz = fd.write(chunk)
                                            fd.flush()
                                            downloaded += sz
                                        else:
                                            logging.error("Chunk not received")
                                except(SSLError):
                                    logging.error("SSL read error has occured on URL: {}".format(src))
                                    jutils.write_to_file(LOG_NAME, "SSL read error -> SRC: {src}, FNAME: {fname}\n".format(code=str(r.status_code), src=src, fname=download_fname), LOG_MUTEX)
                                    failed = True
                                except requests.exceptions.Timeout:
                                    logging.warning("Connection timed out, this may be due to CAPTCHA, please open Kemono and solve the captcha, program will sleep for 20 seconds")
                                    time.sleep(20)
                                except(requests.exceptions.RequestException) as e:
                                    logging.warning(f"{e.__class__.__name__} has occured for {src}, thread sleeping for {self.__connection_timeout} seconds.")
                                    
                                    time.sleep(self.__connection_timeout)
                                except(Exception) as e:
                                    logging.error("Handled an unknown exception: {}".format(e.__class__.__name__))
                                    jutils.write_to_file(LOG_NAME, "Unknown Exception {exc} -> SRC: {src}, FNAME: {fname}\n".format(exc=e.__class__.__name__, code=str(r.status_code), src=src, fname=download_fname), LOG_MUTEX)
                                    failed = True
                                
                        # Checks if unrecoverable error as occured
                        if failed:
                            done = True
                            self.__submit_failure(None)
                        # Checks if the file is correctly downloaded, if so, we are done
                        elif(os.stat(download_fname).st_size == fullsize):
                            done = True
                            logging.debug("Downloaded Size (" + download_fname + ") -> " + str(fullsize))
                            # Increment file download count, file is downloaded at this point
                            self.__submit_downloaded()
                            
                            # Unzip file if specified
                            if self.__unzip and zipextracter.supported_zip_type(download_fname):
                                p = download_fname.rpartition('\\')[0] + "\\" + re.sub(r'[^\w\-_\. ]|[\.]$', '',
                                                        download_fname.rpartition('\\')[2]).rpartition(" by")[0].strip() + "\\"
                                self.__dir_lock.acquire()
                                if not os.path.exists(p):
                                    os.mkdir(p)
                                self.__dir_lock.release()
                                if not zipextracter.extract_zip(download_fname, p, temp=self.__tempextr):
                                    self.__submit_failure("Extraction Failure -> FILE: {fname}\n".format(fname=download_fname))
                        else:
                            logging.warning("File not downloaded correctly, will be restarted!\nSrc: " + src + "\nFname: " + download_fname)
                            time.sleep(self.__connection_timeout)
                            #headers = {'User-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
                            #        'Range': 'bytes=' + str(downloaded) + '-' + str(fullsize)}
                            #mode = 'ab'
                    except(requests.exceptions.RequestException) as e:
                        logging.warning(f"{e.__class__.__name__} has occured for {src}, thread sleeping for {self.__connection_timeout} seconds.")
                        
                        time.sleep(self.__connection_timeout)
                    except FileNotFoundError:
                        logging.debug("Cannot be downloaded, file likely a link, not a file ->" + download_fname)
                        done = True
    
            else:
                self.__submit_skipped()
                self.__existing_file_register_lock.release()
                    
        
        # Increment progress mutex
        if not display_bar:
            self.__progress_mutex.acquire()
            self.__progress.release()
            self.__progress_mutex.release()
        
        # Closes session if session was created within this function
        if close:
            session.close()
        
        # Sleep before exiting
        logging.debug(f"Thread sleeping for {self.__wait} seconds after completing download")
        time.sleep(self.__wait)

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

    def __queue_download_files(self, imgLinks: ResultSet, dir: str, org_dir: str, base_name:str | None, org_base_name:str | None, task_list:Queue|None, counter:PersistentCounter, postcounter:int|None = None) -> Queue:
        """
        Puts all urls in imgLinks in threadpool download queue. If task_list is not None, then
        all urls will be added to task_list instead of being added to download queue.

        Param:
        imgLinks: all image links within a Kemono container
        dir: where to save the images
        base_name: Prefix to name files, None for just a counter
        task_list: list to store tasks into instead of directly processing them, None to directly process them
        counter: a counter to increment for each file and used to rename files
        org_base_name: base name without any additions
        postcounter: counter added to the end of the file name, None to not have one
        
        Raise: DeadThreadPoolException when no download threads are available, ignored if enqueue is false
        Return modified tasklist, is None if task_list param is None
        """
        
        
        if not self.__threads.get_status():
            raise DeadThreadPoolException
        
        if not base_name:
            base_name = ""

        if not org_base_name:
            org_base_name = ""
        
        
        for link in imgLinks:
            href = link.get('href')
            # Type 1 image - Image in Files section
            if href:
                src = href if "http" in href  else self.__container_prefix + href
            # Type 2 image - Image in Content section
            else:
                target = link.get('src') or "" # 我修改的代码
               # Polluted link check, Fanbox is notorious for this
               # Curiously, src can be None as a string
                if "downloads.fanbox" not in target and target != "None":
                     # Hosted on non KMP server
                    if 'http' in target:
                        src = target
                    # Hosted on KMP server
                    else:
                        src = target if "http" in target else self.__container_prefix + target
                else:
                    src = None
                    
            # If a src is detected, it is added to the download queue/task list    
            
            if src:
                logging.debug("Extracted content link: " + src)
                
                # Select the correct download name based on switch
                if self.__download_server_name_type:
                    fname = dir + base_name + self.__trim_fname(src)
                    org_fname = org_dir + base_name + self.__trim_fname(src)
                    
                else:
                    if not postcounter:
                        fname = dir + base_name + str(counter.get()) + '.' + self.__trim_fname(src).rpartition('.')[2]
                        org_fname = org_dir + org_base_name + str(counter.get()) + '.' + self.__trim_fname(src).rpartition('.')[2]          
                    else:
                        fname = dir + base_name + str(counter.get()) + ' (' + str(postcounter) +').' + self.__trim_fname(src).rpartition('.')[2]
                        org_fname = org_dir + org_base_name + str(counter.get()) + '.' + self.__trim_fname(src).rpartition('.')[2]          

                if not task_list:
                    self.__threads.enqueue((self.__download_file, (src, fname, org_fname)))
                else:
                    task_list.put((self.__download_file, (src, fname, org_fname, False)))
                counter.toggle()
        return task_list

    def __download_file_text(self, textLinks:ResultSet, dir:str, base_dir:str) -> None:
        """
        Scrapes all text and their links in textLink and saves it to 
        in dir

        Param:
            textLink: Set of links and their text in Files segment
            dir: Where to save the text and links to. Must be a .txt file
            base_dir: dir without any additions
        """
        frontOffset = 5
        endOffset = 4
        currOffset = 0
        listSz = len(textLinks)
        strBuilder = []
        # No work to be done if the file already exists
        if os.path.exists(base_dir) or listSz <= 9:
            logging.debug(f"File already exists, skipping: {dir}")
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

    def __dupe_file_check(self, org_fname:str, value)->bool:
        """
        Check if dupe file exists

        Args:
            org_fname (str): base name of file
            value: Characteristic of the file
        Return true if dupe file exists, false if does not
        
        Pre: elf.__existing_file_register_lock is already acquired (will not be released)
        """
        values = self.__existing_file_register.hashtable_lookup_value(org_fname)
        
        for i in values[0::2]:
            if i == value:
                return True
        
        return False
            
    
    def __clear_empty(self, dir:str)->None:
        """
        Deletes a directory if it is empty

        Args:
            dir (str): directory to check
        Pre: Handler for exceptions
        """
        if len(os.listdir(dir)) == 0:
            os.rmdir(dir)
    
    def __dupe_file_procedure(self, fname:str, org_fname:str, value:any, lock:bool = False)->bool:
        """
        Checks a file and determines if it already exists on the system. If self.__rename is true,
        a duplicate file may be removed or renamed according to several factors:
        1. If file exists but different name than fname, rename it to fname, return true
        2. If file exists but different name than fname AND another file that is called fname exists, rename it to fname with a counter, return true
        3. If file exists AND name is fname, return true
        4. If file does not exists, return False
        5. If file exists but different name than fname AND another file that is called fname exists and IS EQUAL to the file, delete file, return true

        If self.__rename is false, return bool according to above factors.
        
        Param:
            fname: Full name of file subjected to duplication check
            org_fname: Base name of file subjected to duplication check
            value: Characteristic of the file
            lock: True if self.__existing_file_register_lock is already acquired (will not be released)
        Return: True of the file already exists locally, false if not
        """
        writable = False
        if not lock:
            self.__existing_file_register_lock.acquire()
        #hashed = hash(post_contents)
        values = self.__existing_file_register.hashtable_lookup_value(org_fname)
        # Check 3 conditions when renaming
        if values and self.__rename:
            try:
                # (1) Local file with same name and same size
                index = values.index(value)
                values_copy = values # Markoff list for values
                try:
                    # Since case can occur multiple times, run until exception
                    while True:
                        # Rename local file with same size to fname
                        try:
                            if values[index + 1] != (fname):
                                os.rename(values[index + 1], fname)
                                logging.debug("Base name already exists: {}, Renaming local file {} to {}".format(org_fname, values[index + 1], fname))
                                self.__clear_empty(os.path.dirname(values[index + 1]))
                            values[index + 1] = fname
                            values_copy[index + 1] = None
                            values_copy[index] = None
                            
                        # If file cannot be renamed since a file with the same name exists    
                        except FileExistsError:
                            # File with the name already exists AND have diff size as file to rename -> ignore
                            if fname != values[index + 1] and values[index] != value:
                                logging.debug("Base name already exists: {} skipping file with diff size {}".format(org_fname, values[index + 1]))
                                values_copy[index + 1] = None
                                values[index] = None
                            # File with the same name already exists and has the same size as file to rename -> delete dupe file
                            elif fname != values[index + 1] and values[index] == value:
                                logging.debug("Base name already exists: {} in local file {}, Deleting local file {}".format(org_fname, fname, values[index + 1]))
                                os.remove(values[index + 1])
                                self.__clear_empty(os.path.dirname(values[index + 1]))
                                values = values[0:index] + values[index + 1:]
                                values_copy = values_copy[0:index] + values_copy[index + 1:]
                            # File with the same name is the file to rename -> skip
                            elif values[index + 1] == fname:
                                logging.debug("Base name already exists: {} in local file {}".format(org_fname, values[index + 1]))
                                values_copy[index + 1] = None
                                values[index] = None
                        except (PermissionError, FileNotFoundError) as e:
                            logging.debug(f"{e.__class__.__name__} has occured, unable to perform dupe file procedure on {values[index + 1]} ({org_fname})")
                            values_copy[index + 1] = None
                            values_copy[index] = None
                        # Prepare for next iteration
                        index = values_copy.index(value)
                # At end of first case, update hash table
                except ValueError:
                    self.__existing_file_register.hashtable_edit_value(org_fname, values)
                    writable = False
                
            except ValueError:
                # (2) File cannot be found locally
                writable = True             
            # In cases where file does not exist but is in the register (when scanning a dir multiple times), this step should not be possible to obtain 
            except FileNotFoundError as e:
                logging.debug(f"CRITICAL: {e.__class__.__name__} has occured, unable to perform dupe file procedure on {fname}")
                self.__submit_failure("CRITICAL FAILURE (HASHTABLE); FNAME {src}".format(src=fname))
        # If does not exists, add it and write to file
        elif not values:
            self.__existing_file_register.hashtable_add(KVPair(org_fname, [value, fname]))
            writable = True
        # If not self.__rename, check if dupe file exists
        else:
            for i in values[0::2]:
                if i == value:
                    if not lock:    
                        self.__existing_file_register_lock.release()
                    return False
                writable = True
        if not lock:    
            self.__existing_file_register_lock.release()
        return writable
            

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
            session.max_redirects = 5
            adapter = requests.adapters.HTTPAdapter(pool_connections=self.__tcount, pool_maxsize=self.__tcount, max_retries=0, pool_block=True)
            session.mount('http://', adapter)
            close = True
        else:
            session = self.__sessions[tname.id]    
        
        # Get HTML request and parse the HTML for image links and title ############
        reqs = None
        while not reqs:
            try:
                # reqs = self.__session.get(url, timeout=10, headers=request_headers)
                reqs = fetch_dynamic_content(url, timeout=25, headers=request_headers, root_selector="main#main") # 我修改的代码
            except requests.exceptions.Timeout:
                logging.warning("Connection timed out, this may be due to CAPTCHA, please open Kemono and solve the captcha, program will sleep for 20 seconds")
                time.sleep(20)
            except(requests.exceptions.RequestException) as e:
                logging.warning(f"{e.__class__.__name__} has occured for {url}, thread sleeping for {self.__connection_timeout} seconds.")
                
                time.sleep(self.__connection_timeout)
        soup = BeautifulSoup(reqs.text, 'html.parser')
        while "500 Internal Server Error" in soup.find("title"):
            logging.error("500 Server error encountered at " +
                          url + ", retrying...")
            time.sleep(self.__connection_timeout)
            reqs = None
            while not reqs:
                try:
                    # reqs = self.__session.get(url, timeout=10, headers=request_headers)
                    reqs = fetch_dynamic_content(url, timeout=25, headers=request_headers, root_selector="main#main") # 我修改的代码
                except requests.exceptions.Timeout:
                    logging.warning("Connection timed out, this may be due to CAPTCHA, please open Kemono and solve the captcha, program will sleep for 20 seconds")
                    time.sleep(20)
                except(requests.exceptions.RequestException) as e:
                    logging.warning(f"{e.__class__.__name__} has occured for {url}, thread sleeping for {self.__connection_timeout} seconds.")
                    
                    time.sleep(self.__connection_timeout)
            soup = BeautifulSoup(reqs.text, 'html.parser')
        imgLinks = soup.find_all("a", {'class':'fileThumb'})
        
        # Sleep for a little bit since request was successful
        logging.debug(f"Threading sleeping for {self.__wait} seconds since connection request was successful")
        time.sleep(self.__wait)
        

        # Create a new directory if packed or use artist directory for unpacked
        work_name =  (re.sub(r'[^\w\-_\. ]|[\.]$', '', soup.find("title").text.strip())
             ).split("\\")[0]
        backup = work_name + " - "
        org_work_name = ""
        
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
            
            time_str = None
            id_str = None
            
            if self.__date:
                time_tag = soup.find("div", {'class':'post__published'})
                
                # If is gumroad, time tag can be none
                if time_tag:
                    time_str = time_tag.text.strip().replace(':', '')
                    
            
            if self.__id:
                id_str = url.rpartition("/")[2]
            
            titleDir = os.path.join(root, ((id_str + " ") if id_str else "") + work_name + ((" " + time_str) if time_str else "")) + "\\"
            org_titleDir = os.path.join(root, work_name) + "\\"
            work_name= ""
            
            self.__post_process.append((self.__clear_empty, (titleDir,)))

            
            # Check if directory has been registered ###################################
            self.__register_mutex.acquire()
            value = self.__register.hashtable_lookup_value(titleDir.lower())
            if value != None:  # If register, update titleDir and increment value
                self.__register.hashtable_edit_value(titleDir.lower(), value + 1)
                titleDir = titleDir[:len(titleDir) - 1] + " (" + str(value) + ")\\"
            else:   # If not registered, add to register at value 1
                self.__register.hashtable_add(KVPair[str, int](titleDir.lower(), 1))
                value = 0
            self.__register_mutex.release()
        # For unpacked, all files will be placed in the artist directory
        else:
            
            titleDir = root
            org_titleDir = root
            if self.__date:
                time_tag = soup.find("div", {'class':'post__published'})
                
                # If is gumroad, time tag can be none
                if time_tag:
                    time_str = time_tag.text.strip().replace(':', '')
                else:
                    time_str = None
                
            else:
                time_str = None
                
            if self.__id:
                id_str = url.rpartition("/")[2]
            else:
                id_str = None
            
            org_work_name = work_name + " - "
            work_name = ((id_str + " ") if id_str else "") + work_name + ((" " + time_str) if time_str else "") + " - "

            # Add work_name to register
            self.__register_mutex.acquire()
            value = self.__register.hashtable_lookup_value(work_name.lower())
            if value != None:  # If register, update titleDir and increment value
                self.__register.hashtable_edit_value(work_name.lower(), value + 1)
            else:   # If not registered, add to register at value 1
                self.__register.hashtable_add(KVPair[str, int](work_name.lower(), 1))
                value = 0
            self.__register_mutex.release()
        # Create directory if not registered
        if not os.path.isdir(titleDir):
            os.makedirs(titleDir)
            
        reqs.close()

        # Download all 'files' #####################################################
        # Image type
        if self.__unpacked < 2:
            self.__queue_download_files(imgLinks, titleDir, org_titleDir, work_name, org_work_name, task_list, counter)
        else:
            self.__queue_download_files(imgLinks, titleDir, org_titleDir, work_name, org_work_name, task_list, counter, value if value > 0 else None)
        
        # Link type
        self.__download_file_text(soup.find_all('a', {'target':'_blank'}), titleDir + work_name + "file__text.txt", org_titleDir + org_work_name + "file__text.txt")

        # Scrape post content ######################################################
        content = soup.find("div", class_="post__content")

        # Skip post content is switch is on
        if not self.__exclcontents:
            if content:
                text = content.getText(separator='\n', strip=True)
                if len(text) > 0:
                    # Text section
                    post_contents = ""
                    post_contents += text
                    links = content.find_all("a")
                    for link in links:
                        hr = link.get('href')
                        if not hr:
                            logging.warning("Href returns None at url: {u}".format(u=url))
                        else:
                            post_contents += ("\n" + hr)
                    
                    # Nested content
                    containers = content.find_all("div")
                    prev = None     # Used to get the entire div, not the internal nested divs
                    # 我修改的代码
                    if containers:
                        for container in containers:  
                            # Ignore empty containers
                            if len(container.contents) > 0:
                                
                                # Check if the current container is nested within the previous one
                                if not prev or (prev and not prev.find(container)):
                                    # If not, write to file
                                    post_contents += ("\n" + "Embedded Container: {}".format(container.get_text(strip=True)))
                                
                                # Update prev
                                prev = container
                    
                    hashed = hash(post_contents)
                    writable = self.__dupe_file_procedure(titleDir + work_name + "post__content.txt", org_titleDir + org_work_name + "post__content.txt", hashed)

                    # Write to file
                    if(writable):
                        contents_file =  titleDir + work_name + "post__content.txt"
                        i = 0
                        
                        while(os.path.exists(contents_file)):
                            # Starts at 0 due to backward compatibility with previous dupe naming scheme
                            # predupe case
                            if self.__predupe:
                                contents_file = titleDir + work_name + "(" + str(i) + ") post__content.txt"
                            # postdupe case
                            else:
                                contents_file = titleDir + work_name + "post__content" + " (" + str(i) + ").txt"
                            i += 1
                        jutils.write_utf8(post_contents, contents_file, 'w')
                    
                    
                                    
                
                # Image Section
                if self.__unpacked < 2:
                    task_list = self.__queue_download_files(content.find_all('img'), titleDir, org_titleDir, work_name, org_work_name, task_list, counter)
                else:
                    task_list = self.__queue_download_files(content.find_all('img'), titleDir, org_titleDir, work_name, org_work_name, task_list, counter, value)
        # Download post attachments ##############################################
        attachments = soup.find_all("a", class_="post__attachment-link")
        if attachments:
            for attachment in attachments:
                if not attachment:
                    logging.fatal("No href on {}".format(url))
                download = attachment.get('href')
                # Confirm that mime type of attachment is not html or None
                if download:
                    src = download if "http" in download else self.__container_prefix + download
                    aname =  self.__trim_fname(attachment.text.strip())
                    
                    if self.__unpacked == 2 and value > 0:
                        aname = aname.rpartition('.')[0] + " (" + str(value) + ")." + aname.rpartition(".")[2]
                    # If src does not contain excluded keywords, download it
                    if not self.__exclusion_check(self.__link_name_exclusion, aname):
                        fname = os.path.join(titleDir, work_name + aname)
                        oname = os.path.join(org_titleDir, org_work_name + aname)
                        
                        if task_list:
                            task_list.put((self.__download_file, (src, fname, oname, False)))
                        else:
                            self.__threads.enqueue((self.__download_file, (src, fname, oname)))
        


        # Download post comments ################################################
        # Skip if omit comment switch is on
        if not self.__exclcomments:
            comments = soup.find("div", class_="post__comments")

            # Check for duplicate and writablility
            if comments:
                text = comments.getText(separator='\n', strip=True) 
                if len(text) > 0 and (text and text != "No comments found for this post." and len(text) > 0):
                    hashed = hash(text)
                    writable = self.__dupe_file_procedure(titleDir + work_name + "post__comments.txt", org_titleDir + org_work_name + "post__comments.txt", hashed)

                    # Write to file
                    if(writable):
                        comments_file =  titleDir + work_name + "post__comments.txt"
                        i = 0
                        
                        while(os.path.exists(comments_file)):
                            # Starts at 0 due to backward compatibility with previous dupe naming scheme
                            # predupe case
                            if self.__predupe:
                                comments_file = titleDir + work_name + "(" + str(i) + ") post__comments.txt"
                            # postdupe case
                            else:
                                comments_file = titleDir + work_name + "post__comments" + " (" + str(i) + ").txt"
                            i += 1
                        jutils.write_utf8(text, comments_file, 'w')
                    
            
        # Add to post process queue if partial unpack is on
        if self.__unpacked == 1:
            self.__post_process.append((self.__partial_unpack_post_process, (titleDir, root + backup)))
        
        # Close session if applicable
        if close:
            session.close()
        
        logging.info("Finished scanning {}".format(url))
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
    
    def __partial_unpack_post_process(self, src:str, dest:str)->None:
        """
        Checks if a folder in src is text only or empty, if so, move everything 
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

    def __process_window(self, url: str, continuous: bool, get_list:bool=False, pool:ThreadPool|None=None, stop_url:str = None, override_path:str = None) -> Queue:
        """
        Processes a single main artist window, a window is a page where multiple artist works can be seen

        Param: 
            url: url of the main artist window
            continuous: True to attempt to visit next pages of content, False to not
            get_list: Return a list of tasks instead of processing the data immediately
            pool: None for single thread or an initialized pool for multithreading
            stop_url: url to stop on, is not processed
            override_path: Download path to use
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
                # reqs = self.__session.get(url, timeout=10, headers=request_headers)
                reqs = fetch_dynamic_content(url, timeout=25, headers=request_headers, root_selector="main#main") # 我修改的代码
            except requests.exceptions.Timeout:
                logging.warning("Connection timed out, this may be due to CAPTCHA, please open Kemono and solve the captcha, program will sleep for 20 seconds")
                time.sleep(20)
            except(requests.exceptions.RequestException) as e:
                logging.warning(f"{e.__class__.__name__} has occured for {url}, thread sleeping for {self.__connection_timeout} seconds.")
                
                time.sleep(self.__connection_timeout)
        soup = BeautifulSoup(reqs.text, 'html.parser')
        reqs.close()
        # Create directory
        artist = soup.find("meta", attrs={'name': 'artist_name'})
        titleDir = (override_path if override_path else self.__folder) + re.sub(r'[^\w\-_\. ]|[\.]$', '',
                                          artist.get('content')) + "\\"
        
        # Check to see if artist dir exists
        if not os.path.isdir(titleDir):
            # If updater is used, skip if dir does nto exists
            if self.__update or self.__reupdate:
                logging.warning("{} does not exists! Skipping {}".format(titleDir, artist.get('content')))
                return task_list
            # Otherwise, make the directory
            os.makedirs(titleDir)
        
        contLinks = soup.find_all("a", href=lambda href: href and "/post/" in href)
        suffix = "?o="
        counter = 0
        
        # Update db if window is continuous
        if continuous and self.__db:
            self.__urls.append(url)
            self.__latest_urls.append((contLinks[0]['href'] if "http" in contLinks[0]['href'] else self.__container_prefix + contLinks[0]['href']) if len(contLinks) > 0 else None)
            self.__override_paths.append(override_path if override_path else self.__folder)
            self.__artist.append(artist.get('content'))
           
        # Process each window
        while contLinks:
            # Process all links on page
            for link in contLinks:
                content = link['href']
                
                # Generate check url
                checkurl = content if "http" in content else self.__container_prefix + content
                
                if stop_url == None:
                    stop_url = checkurl
                # If stop url is encounter, return from the function
                elif(checkurl == stop_url):
                    return task_list
                
                pool.enqueue((self.__process_container, (content if "http" in content else self.__container_prefix + content, titleDir, task_list,)))
            if continuous:
                # Move to next window
                counter += 50       # Adjusted to 50 for the new site
                reqs = None
                while not reqs:
                    try:
                        # reqs = self.__session.get(url + suffix + str(counter), timeout=10, headers=request_headers)
                        reqs = fetch_dynamic_content(url + suffix + str(counter), timeout=25, headers=request_headers, root_selector="main#main") # 我修改的代码
                    except requests.exceptions.Timeout:
                        logging.warning("Connection timed out, this may be due to CAPTCHA, please open Kemono and solve the captcha, program will sleep for 20 seconds")
                        time.sleep(20)
                    except(requests.exceptions.RequestException) as e:
                        logging.warning(f"{e.__class__.__name__} has occured for {url + suffix + str(counter)}, thread sleeping for {self.__connection_timeout} seconds.")
                        
                        time.sleep(self.__connection_timeout)
                soup = BeautifulSoup(reqs.text, 'html.parser')
                reqs.close()
                contLinks = soup.find_all("a", href=lambda href: href and "/post/" in href)
            else:
                contLinks = None
        return task_list


    def __download_discord_js(self, jsList:dict, titleDir:str, get_list:bool) -> list[str] | tuple:
        """
        Downloads any file found in js and returns text data

        TODO update
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
                    if(i.get('path')):
                        if "https" != i.get('path')[0:5]:
                            url = i.get('path') if "http" in i.get('path') else self.__container_prefix + i.get('path')
                        else:
                            url = i.get('path')
                        stringBuilder.append(url + '\n\n')
                        
                        
                        # Download the attachment
                        if get_list:
                            task_list.append((self.__download_file, (url, imageDir + str(counter) + '.' + url.rpartition('.')[2], str(counter) + '.' + url.rpartition('.')[2], False)))
                        else:
                            self.__threads.enqueue((self.__download_file, (url, imageDir + str(counter) + '.' + url.rpartition('.')[2], str(counter) + '.' + url.rpartition('.')[2])))
                        counter += 1
                        # If is on the register, do not download the attachment

        # Write to file
        return stringBuilder if(not get_list) else (stringBuilder, task_list,)

    def __process_discord_server(self, serverJs:dict, titleDir:str, get_list:bool) -> list|None:
        """
        Process a discord server

        TODO UPDATE
        Param:
            serverJS: discord server json token, in format {"id":xxx,"name":xxx}
            titleDir: Where to store discord content, absolute directory ends with '\\'
        """
        dir = titleDir + serverJs.get('name') + '\\'
        # Make sure a dupe directory does not exists, if so, adjust dir name
        value = self.__register.hashtable_lookup_value(dir.lower())
        if value != None:  # If register, update titleDir and increment value
            self.__register.hashtable_edit_value(dir.lower(), value + 1)
            dir = dir[0:len(dir) - 1] + " (" + str(value) + ")\\"
        else:   # If not registered, add to register at value 1
            self.__register.hashtable_add(KVPair[str, int](dir.lower(), 1))

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

        TODO UPDATE
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
                    # reqs = self.__session.get(url, timeout=10, headers=request_headers)
                    reqs = fetch_dynamic_content(url, timeout=25, headers=request_headers, root_selector="main#main") # 我修改的代码
                except requests.exceptions.Timeout:
                    logging.warning("Connection timed out, this may be due to CAPTCHA, please open Kemono and solve the captcha, program will sleep for 20 seconds")
                    time.sleep(20)
                except(requests.exceptions.RequestException) as e:
                    logging.warning(f"{e.__class__.__name__} has occured for {url}, thread sleeping for {self.__connection_timeout} seconds.")
                    
                    time.sleep(self.__connection_timeout)
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

            # Add entry to database
            #if self.__db:
            #    self.__db.execute(("INSERT INTO Parent VALUES (?, 'Kemono', ?)", (url, self.__folder + url.rpartition('/')[2] + "\\")))

        # For multiple window pages
        elif 'user' in url:
            task_list = self.__process_window(url, True, get_list=get_list, pool=scrape_pool)
            
            # As artist name is unknown, we update the database within process_window()
    
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

    def monitor_queue(self, q:Queue, resp:str|None=None)->None:
        """
        Block until q is joined, displays resp afterwards 

        Args:
            q (Queue): q to block until joined
        """
        q.join()
        if resp:
            logging.info(resp)
    
    def __prog_bar(self, max:int)->None:
        """
        Display a progress bar, thread will be locked until internal counter reaches max.
        Counter is incremented when self.__progress is released
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
        
        
        if self.__update or self.__reupdate:
            # Get all artists and their destinations from database
            rows = None
            while not rows:
                try:
                    rows = self.__db.execute("SELECT * FROM Parent2").fetchall()
                except sqlite3.OperationalError:
                    logging.warning(traceback.format_exc)
                    logging.warning("Database is locked, waiting 10s before trying again")
                    time.sleep(10)
            
            
            
            # Compile a list of urls, their download path, and latest url while using custom prefix.
            url = [self.__container_prefix + "/" + row[0][8:].partition("/")[2] for row in rows]
            latest = [self.__container_prefix + "/" + row[3][8:].partition("/")[2] for row in rows] if not self.__reupdate else [None] * len(url)
            path = [row[4] for row in rows]
            
            assert(len(url) == len(latest))
            assert(len(url) == len(path))
            
            # Add all new urls to the queue list
            scrape_pool = ThreadPool(self.__tcount)
            scrape_pool.start_threads()
            for i in range(0, len(url)):
                logging.info("Fetching {url}".format(url=url[i]))
                queue_list.append(self.__process_window(url[i], True, True, scrape_pool, latest[i], path[i]))
                
            
            scrape_pool.join_queue()
            scrape_pool.kill_threads()
            
        else:
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
                while not url or self.__container_prefix not in url:
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
        logging.info("Files skipped: " + str(self.__scount))
        if self.__failed > 0:
            logging.info("Failed: {failed}, stored in {log}".format(failed=self.__failed, log=LOG_NAME))
    
    
    def routine(self, url: str | list[str] | None, unpacked:int | None) -> None:
        """
        NOTE: DEPRECATED, PLEACE USE alt_routine() instead!!!
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
        
        if self.__update or self.__reupdate:
            # Get all artists and their destinations from database
            rows = None
            while not rows:
                try:
                    rows = self.__db.execute("SELECT * FROM Parent2").fetchall()
                except sqlite3.OperationalError:
                    logging.warning(traceback.format_exc)
                    logging.warning("Database is locked, waiting 10s before trying again")
                    time.sleep(10)
            
            # Compile a list of urls, their download path, and latest url
            url = [row[0] for row in rows]
            latest = [row[3] for row in rows] if not self.__reupdate else [None] * len(url)
            path = [row[4] for row in rows]
            
            # Add all new urls to the queue list
            scrape_pool = ThreadPool(self.__tcount)
            scrape_pool.start_threads()
            for i in range(0, len(url)):
                logging.info("Fetching {url}".format(url=url[i]))                
                self.__process_window(url[i], True, False, scrape_pool, latest[i], path[i])
            
            scrape_pool.join_queue()
            scrape_pool.kill_threads()
        else:    
            
            # Get url to download ######################
            # List type url
            if isinstance(url, list):
                for line in url:
                    line = line.strip()
                    if len(line) > 0:
                        self.__call_and_interpret_url(line)

            # User input url
            else:
                while not url or self.__container_prefix not in url:
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
    logging.info("List of all switches, please take note of what switches are required:")
    logging.info("DOWNLOAD CONFIG - How files are downloaded\n\
        -f --bulkfile <textfile.txt> : Bulk download from text file containing links\n\
        -d --downloadpath <path> : REQUIRED - Set download path for single instance, must use '\\' or '/'\n\
        -c --chunksz <#> : Adjust download chunk size in bytes (Default is 64M)\n\
        -t --threadct <#> : Change download thread count (default is 1, max is 5)\n\
        -w --wait <#> : Delay between downloads in seconds (default is 2.0s and cannot be set lower)\n\
        -b --track : Track artists which can updated later, not supported for discord\n\
        -a --predupe : Prepend () instead of postpending in duplicate file case\n\
        -g --updatedb <db_name.db>: Set db name to use for the update db (default is KMP.db)\n\
        -i --formats \"image, audio, 7z, ...\": Set download file formats, corresponds to content-type header in HTTP response\n\
        -j --prefix <url prefix>: Set prefix of kemono url. DOES NOT END IN \"\\\". Does not affect databases. default is \"https://kemono.party\".\n\
        -k --disableprescan: Disables prescan used to catelog existing files. Disabling reduces dupe file check accuracy in exchange for lower memory usage and lowered run time.\n\
        -w --date: Disable appending date to file and/or folder names.\n\
        --id: Disable prepending id to file and/or folder names.\n")
        
    
    logging.info("EXCLUSION - Exclusion of specific downloads\n\
        -x --excludefile \"txt, zip, ..., png\" : Exclude files with listed extensions, NO '.'s\n\
        -p --excludepost \"keyword1, keyword2,...\" : Keyword in excluded posts, not case sensitive\n\
        -l --excludelink \"keyword1, keyword2,...\" : Keyword in excluded link, not case sensitive. Is for link plaintext, not its target\n\
        -o --omitcomment : Do not download any post comments\n\
        -m --omitcontent : Do not download any textual post contents\n\
        -n --minsize <min_size>: Minimum file size in bytes\n")
    
    logging.info("DOWNLOAD FILE STRUCTURE - How to organize downloads\n\
        -s --partialunpack : If a artist post is text only, do not create a dedicated directory for it, partially unpacks files\n\
        -u --unpacked : Enable unpacked file organization, all works will not have their own folder, overrides partial unpack\n\
        -e --hashname : Download server name instead of program defined naming scheme, may lead to issues if Kemono does not store links correctly. Not supported for Discord\n\
        -v --unzip : Enables unzipping of files automatically, requires 7z and setup to be done correctly\n\
        -q --logging <#> : Set logging level. 1 == info (default), 2 == debug, 3 == debug but print output to debug_log.txt. Program will initially begin in level 1.\n\
            Note that logging output is redirected to debug_log.txt for level 3 and opening the file while the program is running will crash the program.\n")
    
    logging.info("UTILITIES - Things that can be done besides downloading\n\
        --UPDATE : Update all tracked artist works. If an entry points to a nonexistant directory, the artist will be skipped.\n\
        --REUPDATE : Redownload all tracked artist works\n\
        --RENAME : Rename existing files instead of skipping them with current switch config. Only works with --id and --rename as of now.\n")
    
    logging.info("TROUBLESHOOTING - Solutions to possible issues\n\
        -z --httpcode \"500, 502,...\" : HTTP codes to retry downloads on, default is 429 and 403\n\
        -r --maxretries <#> : Maximum number of HTTP code retries, default is 10 (negative for infinite which is highly unrecommended)\n\
        -h --help : Help\n\
        --DEPRECATED : Enable deprecated download mode\n\
        --BENCHMARK : Benchmark experiemental mode's scraping speed, does not download anything\n")

def main() -> None:
    """
    Program runner
    """
    # Clear scr
    os.system('cls')
    
    # Preliminaries
    start_time = time.monotonic()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s (%(asctime)s): %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    folder = False
    urls = False
    unzip = False
    tcount = -1
    wait = -1
    chunksz = -1
    unpacked = False
    excluded:list = []
    retries = 10
    partial_unpack = False
    http_codes = []
    post_excluded = []
    server_name = False
    link_excluded = []
    deprecated = False
    benchmark = False
    db_name = 'KMP.db'
    update = False
    track = False
    exclcomments = False
    exclcontents = False
    predupe = False
    minsize = 0
    reupdate = False
    prefix = "https://kemono.party"
    disableprescan = False
    date = True
    id = True
    rename = False
    if len(sys.argv) > 1:
        pointer = 1
        while(len(sys.argv) > pointer):
            try:
                if (sys.argv[pointer] == '-f' or  sys.argv[pointer] == '--bulkfile') and len(sys.argv) >= pointer:
                    with open(sys.argv[pointer + 1], "r") as fd:
                        urls = fd.readlines()
                    pointer += 2
                elif sys.argv[pointer] == '-v' or sys.argv[pointer] == '--unzip':
                    unzip = True
                    pointer += 1
                    logging.info("UNZIP -> " + str(unzip))
                elif sys.argv[pointer] == '-w' or sys.argv[pointer] == '--date':
                    date = False
                    pointer += 1
                    logging.info("APPEND DATE -> " + str(date))
                elif sys.argv[pointer] == '--id':
                    id = False
                    pointer += 1
                    logging.info("PREPEND ID -> " + str(id))
                elif sys.argv[pointer] == '--DEPRECATED':
                    deprecated = True
                    pointer += 1
                    logging.info("DEPRECATED -> " + str(deprecated))
                elif sys.argv[pointer] == '-b' or sys.argv[pointer] == '--track':
                    track = True
                    pointer += 1
                    logging.info("TRACK -> " + str(track))
                elif sys.argv[pointer] == '-o' or sys.argv[pointer] == '--omitcomment':
                    exclcomments = True
                    pointer += 1
                    logging.info("OMITCOMMENTS -> " + str(exclcomments))
                elif sys.argv[pointer] == '-m' or sys.argv[pointer] == '--omitcontent':
                    exclcontents = True
                    pointer += 1 
                    logging.info("OMITPOSTCONTENT -> " + str(exclcontents))
                elif (sys.argv[pointer] == '-n' or sys.argv[pointer] == '--minsize') and len(sys.argv) >= pointer:
                    minsize = int(sys.argv[pointer + 1])
                    pointer += 2
                    logging.info("MINFILESIZE -> " + str(minsize))
                elif sys.argv[pointer] == '--UPDATE':
                    update = True
                    pointer += 1
                    logging.info("UPDATE -> " + str(update))
                elif sys.argv[pointer] == '--RENAME':
                    rename = True
                    pointer += 1
                    logging.info("RENAME -> " + str(rename))
                elif sys.argv[pointer] == '--REUPDATE':
                    reupdate = True
                    pointer += 1
                    logging.info("REUPDATE -> " + str(reupdate))
                elif sys.argv[pointer] == '--REUPDATE':
                    reupdate = True
                    pointer += 1
                    logging.info("REUPDATE -> " + str(reupdate))
                elif sys.argv[pointer] == '-e' or sys.argv[pointer] == '--hashname':
                    server_name = True
                    pointer += 1
                    logging.info("SERVER_NAME_DOWNLOAD -> " + str(server_name))          
                elif sys.argv[pointer] == '-a' or sys.argv[pointer] == '--predupe':
                    predupe = True
                    pointer += 1
                    logging.info("PREDUPE -> " + str(predupe))          
                elif sys.argv[pointer] == '-k' or sys.argv[pointer] == '--disableprescan':
                    disableprescan = True
                    pointer += 1
                    logging.info("DISABLE PRESCAN -> " + str(disableprescan))       
                elif sys.argv[pointer] == '-u' or sys.argv[pointer] == '--unpacked':
                    unpacked = True
                    partial_unpack = False
                    pointer += 1
                    logging.info("UNPACKED -> " + str(unpacked))
                elif sys.argv[pointer] == '--BENCHMARK':
                    benchmark = True
                    pointer += 1
                    logging.info("BENCHMARK -> TRUE")
                elif (sys.argv[pointer] == '-d' or sys.argv[pointer] == '--downloadpath') and len(sys.argv) >= pointer:
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
                elif (sys.argv[pointer] == '-t' or sys.argv[pointer] == '--threadct') and len(sys.argv) >= pointer:
                    tcount = int(sys.argv[pointer + 1])
                    pointer += 2
                    logging.info("DOWNLOAD_THREAD_COUNT -> " + str(tcount))
                elif (sys.argv[pointer] == '-q' or sys.argv[pointer] == '--logging') and len(sys.argv) >= pointer:
                    log_level =  int(sys.argv[pointer + 1])
                    match log_level:
                        case 2:
                            logging.basicConfig(level=9, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', force=True)
                        case 3:
                            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='debug_log.txt', filemode='w', force=True)
                        case _:
                            logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', force=True)
                    pointer += 2
                elif (sys.argv[pointer] == '-j' or sys.argv[pointer] == '--prefix') and len(sys.argv) >= pointer:
                    prefix = (sys.argv[pointer + 1])
                    pointer += 2
                    logging.info("PREFIX -> " + prefix)
                elif (sys.argv[pointer] == '-w' or sys.argv[pointer] == '--wait') and len(sys.argv) >= pointer:
                    wait = float(sys.argv[pointer + 1])
                    pointer += 2
                    logging.info("DELAY_BETWEEN_DOWNLOADS -> " + str(wait))
                elif (sys.argv[pointer] == '-g' or sys.argv[pointer] == '--updatedb') and len(sys.argv) >= pointer:
                    db_name = sys.argv[pointer + 1]
                    pointer += 2
                    logging.info("UPDATE_DB_NAME -> " + db_name)
                elif (sys.argv[pointer] == '-c' or sys.argv[pointer] == '--chunksz') and len(sys.argv) >= pointer:
                    chunksz = int(sys.argv[pointer + 1])
                    pointer += 2
                    logging.info("CHUNKSZ -> " + str(chunksz))
                elif (sys.argv[pointer] == '-r' or sys.argv[pointer] == '--maxretries') and len(sys.argv) >= pointer:
                    retries = int(sys.argv[pointer + 1])
                    pointer += 2
                    logging.info("RETRIES -> " + str(retries))
                elif (sys.argv[pointer] == '-x' or sys.argv[pointer] == '--excludefile') and len(sys.argv) >= pointer:
                    
                    for ext in sys.argv[pointer + 1].split(','):
                        excluded.append(ext.strip().lower())
                    pointer += 2
                    logging.info("EXT_EXCLUDED -> " + str(excluded))
                elif (sys.argv[pointer] == '-l' or sys.argv[pointer] == '--excludelink') and len(sys.argv) >= pointer:
                    
                    for ext in sys.argv[pointer + 1].split(','):
                        link_excluded.append(ext.strip().lower())
                    pointer += 2
                    logging.info("LINK_EXCLUDED -> " + str(link_excluded))
                elif (sys.argv[pointer] == '-p' or sys.argv[pointer] == '--excludepost') and len(sys.argv) >= pointer:
                    
                    for ext in sys.argv[pointer + 1].split(','):
                        post_excluded.append(ext.strip().lower())
                    pointer += 2
                    logging.info("POST_EXCLUDED -> " + str(post_excluded))
                
                elif (sys.argv[pointer] == '-i' or sys.argv[pointer] == '--formats') and len(sys.argv) >= pointer:
                    formats = []
                    for ext in sys.argv[pointer + 1].split(','):
                        formats.append(ext.strip().lower())
                    pointer += 2
                    global download_format_types
                    download_format_types = formats
                    logging.info("DOWNLOAD FORMATS -> " + str(download_format_types))
                elif (sys.argv[pointer] == '-z' or sys.argv[pointer] == '--httpcode') and len(sys.argv) >= pointer:
                    
                    for ext in sys.argv[pointer + 1].split(','):
                        http_codes.append(int(ext.strip()))
                    pointer += 2
                    logging.info("HTTP CODES -> " + str(http_codes))
                elif sys.argv[pointer] == '-s' or sys.argv[pointer] == '--partialunpack':
                    if not unpacked:
                        partial_unpack = True
                        logging.info("PARTIAL_UNPACK -> " + str(partial_unpack))
                        pointer += 1
                else:
                    logging.error(f"{sys.argv[pointer]} is not a valid configuration!")
                    exit(0)
            except IndexError:
                logging.error(f"Missing argument for {sys.argv[pointer]}")
                exit(0)

    # Prelim dirs
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)

    # Run the downloader
    if folder or update or reupdate:
        print("\n____________________________________________________________________________________________________")
        logging.warning("YOU MAY NEED TO VISIT KEMONO.PARTY OR KEMONO.SU AND SOLVE THE CAPTCHA BEFORE RUNNING THE PROGRAM.")
        logging.warning("IF YOUR DOWNLOAD APPEARS STUCK, UPDATE THE USER-AGENT IN user_agent.txt")
        print("____________________________________________________________________________________________________\n")
        # Pull latest user agent
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "user-agent.txt")) as fd:
            agent = fd.read().strip()
        
        # Update user agent
        global request_headers
        request_headers['User-agent'] = agent
        
        downloader = KMP(folder, unzip, tcount, chunksz, ext_blacklist=excluded, timeout=retries, http_codes=http_codes, post_name_exclusion=post_excluded,\
            download_server_name_type=server_name, link_name_exclusion=link_excluded, wait=wait, db_name=db_name, track=track, update=update, exclcomments=exclcomments,\
                exclcontents=exclcontents, minsize=minsize, predupe=predupe, reupdate=reupdate, prefix=prefix, disableprescan=disableprescan, date=date, id=id, rename=rename)

        if not deprecated or benchmark:
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