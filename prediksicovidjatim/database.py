import os
import psycopg2
import psycopg2.pool
from psycopg2.extras import DictCursor, execute_batch
from contextlib import contextmanager
from dotenv import load_dotenv
from threading import Semaphore
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

singleton = None

class Database:
    
    def __init__(self, url=None, min=0, max=10):
        self.init(url, min, max)
    
    def init(self, url=None, min=0, max=10):
        self.db_url = url or DATABASE_URL
        self.conn_pool = psycopg2.pool.ThreadedConnectionPool(min, max, self.db_url)
        self._semaphore = Semaphore(max)
        
    @contextmanager
    def get_conn(self, key=None):
        conn=None
        try:
            self._semaphore.acquire()
            conn = self.conn_pool.getconn(key)
            '''
            with conn:
                yield conn
            '''
            yield conn
        except:
            raise
        finally:
            if conn:
                self.put_conn(conn, key)
            
    def put_conn(self, conn, key=None):
        self.conn_pool.putconn(conn, key)
        self._semaphore.release()
        
    def close_all(self):
        return self.conn_pool.closeall()
        
    def get_pool(self):
        return self.conn_pool

def init(url=None, min=0, max=10):
    global singleton
    if singleton:
        singleton.close_all()
    singleton = Database(url, min, max)

def get_conn(key=None):
    if not singleton:
        raise Exception("Please init database first")
    return singleton.get_conn(key)
    
def put_conn(conn, key=None):
    if not singleton:
        raise Exception("Please init database first")
    return singleton.put_conn(conn, key)
    
def close_all():
    if not singleton:
        raise Exception("Please init database first")
    return singleton.close_all()
    
def get_pool():
    if not singleton:
        raise Exception("Please init database first")
    return singleton.get_pool()
    
def get_singleton():
    return singleton