# ./00_html_content_collector/db_manager.py
import sqlite3
import json
from sqlite3 import Error
from typing import Optional, Tuple
from custom_exceptions import DatabaseError
from logger import setup_logging, log_error, log_info

# Initialize loggers
loggers = setup_logging(output_dir='logs', doc_name='db_manager', version='v1')

def create_connection() -> Optional[sqlite3.Connection]:
    try:
        conn = sqlite3.connect('scraper_data.db')
        return conn
    except Error as e:
        log_error(loggers, f"Error connecting to database: {e}")
        raise DatabaseError(f"Failed to connect to database: {str(e)}")

def init_db() -> None:
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS pages
                         (url TEXT PRIMARY KEY, content TEXT, checksum TEXT, last_updated TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS scrape_progress
                         (url TEXT PRIMARY KEY, last_scraped TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS link_integrity
                         (url TEXT PRIMARY KEY, status_code INTEGER, is_redirect BOOLEAN, final_url TEXT,
                          content_type TEXT, is_internal BOOLEAN, anchor_exists BOOLEAN)''')
            c.execute('''CREATE TABLE IF NOT EXISTS page_headers
                         (url TEXT PRIMARY KEY, headers TEXT, last_updated TIMESTAMP)''')
            conn.commit()
            log_info(loggers, "Database initialized successfully")
        except Error as e:
            log_error(loggers, f"Error creating database tables: {e}")
            raise DatabaseError(f"Failed to create database tables: {str(e)}")
        finally:
            conn.close()
    else:
        log_error(loggers, "Error! Cannot create the database connection.")
        raise DatabaseError("Failed to create database connection")

def save_page(url: str, content: str, checksum: str, headers: dict) -> None:
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO pages VALUES (?, ?, ?, datetime('now'))", (url, content, checksum))
            headers_json = json.dumps(headers)
            c.execute("INSERT OR REPLACE INTO page_headers VALUES (?, ?, datetime('now'))", (url, headers_json))
            conn.commit()
            log_info(loggers, f"Page saved successfully: {url}")
        except Error as e:
            log_error(loggers, f"Error saving page and headers: {e}")
            raise DatabaseError(f"Failed to save page and headers: {str(e)}")
        finally:
            conn.close()
    else:
        log_error(loggers, "Error! Cannot create the database connection.")
        raise DatabaseError("Failed to create database connection")

def get_page_update_frequency(url: str) -> float:
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("""
                SELECT COUNT(*) as update_count,
                       MIN(julianday('now') - julianday(last_updated)) as days_since_last_update
                FROM pages
                WHERE url = ? AND last_updated > datetime('now', '-30 days')
            """, (url,))
            result = c.fetchone()
            if result:
                update_count, days_since_last_update = result
                if days_since_last_update is not None:
                    return update_count / (days_since_last_update + 1)  # Adding 1 to avoid division by zero
            return 0
        except Error as e:
            log_error(loggers, f"Error getting page update frequency: {e}")
            raise DatabaseError(f"Failed to get page update frequency: {str(e)}")
        finally:
            conn.close()
    else:
        log_error(loggers, "Error! Cannot create the database connection.")
        raise DatabaseError("Failed to create database connection")

def save_scrape_progress(url: str) -> None:
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO scrape_progress VALUES (?, datetime('now'))", (url,))
            conn.commit()
            log_info(loggers, f"Scrape progress saved: {url}")
        except Error as e:
            log_error(loggers, f"Error saving scrape progress: {e}")
            raise DatabaseError(f"Failed to save scrape progress: {str(e)}")
        finally:
            conn.close()
    else:
        log_error(loggers, "Error! Cannot create the database connection.")
        raise DatabaseError("Failed to create database connection")

def get_last_scraped_url() -> Optional[str]:
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT url FROM scrape_progress ORDER BY last_scraped DESC LIMIT 1")
            result = c.fetchone()
            return result[0] if result else None
        except Error as e:
            log_error(loggers, f"Error getting last scraped URL: {e}")
            raise DatabaseError(f"Failed to get last scraped URL: {str(e)}")
        finally:
            conn.close()
    else:
        log_error(loggers, "Error! Cannot create the database connection.")
        raise DatabaseError("Failed to create database connection")

def load_checksum(url: str) -> Optional[str]:
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT checksum FROM pages WHERE url = ?", (url,))
            result = c.fetchone()
            return result[0] if result else None
        except Error as e:
            log_error(loggers, f"Error loading checksum: {e}")
            raise DatabaseError(f"Failed to load checksum: {str(e)}")
        finally:
            conn.close()
    else:
        log_error(loggers, "Error! Cannot create the database connection.")
        raise DatabaseError("Failed to create database connection")
