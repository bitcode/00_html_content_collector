# Documentation Scraper

This project is a web scraper designed to download HTML content from a documentation website. The scraper follows links within the specified domain and path, excluding media files, and saves the downloaded HTML files to a local directory structure mirroring the URL structure. It also converts SVG diagrams to PNG images and includes them in the HTML files.

## Features

- **Scrapes HTML content** from a specified documentation website.
- **Follows internal links** within the specified domain and path.
- **Excludes media files** (PNG, JPG, JPEG, GIF, PDF).
- **Saves downloaded HTML files** to a local directory structure.
- **Converts inline SVG diagrams to PNG** and includes them in HTML files.
- **Extracts SVG content from iframes**, converts to PNG, and replaces iframes with image tags.
- **Implements a delay between requests** to avoid overloading the server.
- **Logs scraping activity and errors** to a file named `app.log`.
- **Handles network-related errors** and unhandled status codes.
- **Avoids re-downloading already scraped pages**.
- **Implements JavaScript rendering** for dynamic content.
- **Performs content cleaning and normalization**.
- **Extracts and stores metadata** and structured data.
- **Database operations**:
  - Stores page content and metadata in a SQLite database.
  - Tracks scraping progress.
  - Checks link integrity.
  - Manages content hashing for efficient updates.
- **Rate limiting** with dynamic adjustment.
- **Scheduled scraping** using the `schedule` module.
- **Proxy management** for large-scale scraping.

## Project Structure

- `downloaded_html/`: Directory where the downloaded HTML files will be saved.
- `logger.py`: Module for setting up logging.
- `main.py`: Main script to start the scraping process.
- `config.py`: Configuration settings for the project.
- `scraper.py`: Module containing the core scraping functions.
- `scheduled_scrape.py`: Script for scheduled scraping tasks.
- `requirements.txt`: List of required Python packages.
- `setup.cfg`: Configuration for code style.
- `TODO.md`: Project roadmap and TODO list.
- `README.md`: This file.

## Dependencies

The project relies on several Python packages, including:

- requests
- beautifulsoup4
- cairosvg
- selenium
- langdetect
- extruct
- schedule
- sqlite3

For a complete list of dependencies, refer to the `requirements.txt` file.

## Setup and Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/documentation-scraper.git
    cd documentation-scraper
    ```

2. **Install the required dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Set up the configuration**:
    - Update the `base_url` in `main.py` to the desired documentation website.
    - Ensure the `core_manifest.json` file is present in the parent directory of the project.

4. **Initialize the database**:
    ```bash
    python -c "from scraper import init_db; init_db()"
    ```

## Usage

### Running the Scraper

To run the scraper, use the following command:

```bash
python main.py <doc_name> <version> [--initial_delay INITIAL_DELAY] [--concurrent] [--max_workers MAX_WORKERS]
```

- `<doc_name>`: The name of the documentation to scrape (as specified in core_manifest.json).
- `<version>`: The version of the documentation to scrape.
- `--initial_delay`: Initial delay between requests in seconds (default: 3).
- `--concurrent`: Use concurrent scraping (default: False).
- `--max_workers`: Maximum number of concurrent workers (only used with --concurrent, default: 5).

## Project Structure

- `downloaded_html/`: Directory where the downloaded HTML files will be saved
- `logger.py`: Module for setting up logging
- `main.py`: Main script to start the scraping process
- `requirements.txt`: List of required Python packages
- `scraper.py`: Module containing the core scraping functions

## Dependencies

The project relies on several Python packages, including:

- requests
- beautifulsoup4
- cairosvg
- selenium
- langdetect
- extruct

For a complete list of dependencies, refer to the `requirements.txt` file.

## Customization

You can customize the scraper behavior by modifying the following parameters in `main.py`:

- `base_url`: The starting URL for the documentation website
- `delay`: The time delay between requests (default is 3 seconds)

## Logging

The scraper logs its activity to both a file (`app.log`) and the console. You can adjust the logging level in `logger.py` if needed.

## Database Operations

The scraper uses a SQLite database (`scraper_data.db`) to:

- **Track Scraping Progress**:
  - Stores the URLs of pages that have been scraped along with timestamps.
  - This allows the scraper to resume from where it left off in case of interruptions and to avoid re-scraping pages unnecessarily.

- **Manage Content Hashes**:
  - Stores hashes of the content of each page.
  - These hashes are used to detect changes in content, allowing the scraper to update only those pages that have changed since the last scrape.

- **Link Integrity Checks**:
  - Stores the results of link integrity checks, including status codes, final URLs after redirects, and whether internal links are valid.
  - This information helps in maintaining the quality and consistency of the scraped data.

- **Store Metadata**:
  - Extracted metadata such as titles, descriptions, keywords, last modified dates, and structured data are stored in the database.
  - This metadata can be useful for various analytical purposes and for improving the scraping process.

The actual scraped content, including HTML files and images, is saved directly to the filesystem in a directory structure that mirrors the URL paths. This approach allows for efficient storage and easy access to the content without the overhead of storing large amounts of data in the database.


### Roadmap

For a more detailed view of our roadmap, please see our [TODO.md](TODO.md) file.

## License

This project is open-source and available under the [MIT License](LICENSE).
