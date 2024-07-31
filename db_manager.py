import sqlite3
import json
from sqlite3 import Error

def create_connection():
    try:
        conn = sqlite3.connect('scraper_data.db')
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None


def init_db():
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
        except Error as e:
            print(f"Error creating database tables: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")


def save_page(url, content, checksum, headers):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO pages VALUES (?, ?, ?, datetime('now'))", (url, content, checksum))
            headers_json = json.dumps(headers)
            c.execute("INSERT OR REPLACE INTO page_headers VALUES (?, ?, datetime('now'))", (url, headers_json))
            conn.commit()
        except Error as e:
            print(f"Error saving page and headers: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")


def get_page_update_frequency(url):
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
            print(f"Error getting page update frequency: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")
    return 0


def save_scrape_progress(url):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO scrape_progress VALUES (?, datetime('now'))", (url,))
            conn.commit()
        except Error as e:
            print(f"Error saving scrape progress: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")


def get_last_scraped_url():
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT url FROM scrape_progress ORDER BY last_scraped DESC LIMIT 1")
            result = c.fetchone()
            return result[0] if result else None
        except Error as e:
            print(f"Error getting last scraped URL: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")
    return None


def load_checksum(url):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT checksum FROM pages WHERE url = ?", (url,))
            result = c.fetchone()
            return result[0] if result else None
        except Error as e:
            print(f"Error loading checksum: {e}")
        finally:
            conn.close()
    return None
