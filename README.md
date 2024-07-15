# Documentation Scraper

This project is a web scraper designed to download HTML content from a documentation website. The scraper follows links within the specified domain and path, excluding media files, and saves the downloaded HTML files to a local directory structure mirroring the URL structure. It also converts SVG diagrams to PNG images and includes them in the HTML files.

## Features

- Scrapes HTML content from a specified documentation website
- Follows internal links within the specified domain and path
- Excludes media files (PNG, JPG, JPEG, GIF, PDF)
- Saves downloaded HTML files to a local directory structure
- Converts inline SVG diagrams to PNG and includes them in HTML files
- Extracts SVG content from iframes, converts to PNG, and replaces iframes with image tags
- Implements a delay between requests to avoid overloading the server
- Logs scraping activity and errors to a file named `app.log`
- Handles network-related errors and unhandled status codes
- Avoids re-downloading already scraped pages
- Implements JavaScript rendering for dynamic content
- Performs content cleaning and normalization
- Extracts and stores metadata and structured data

## Usage

1. Clone the repository.
2. Install the required dependencies by running `pip install -r requirements.txt`.
3. Update the `base_url` in `main.py` to the desired documentation website.
4. Run the scraper by executing `python main.py`.

The scraper will start downloading the HTML content from the base URL and save the files to the `downloaded_html` directory. The scraping progress and any errors will be logged in the `app.log` file.

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

## Roadmap

Our project roadmap outlines the upcoming features and improvements:

### HTML Content Collector Improvements

- [ ] Implement robots.txt compliance
- [x] Add sitemap.xml parsing
- [x] Enhance rate limiting with dynamic adjustment
- [x] Implement content hashing for efficient updates
- [x] Add metadata extraction (title, description, keywords, last modified date)
- [ ] Improve error handling with automatic retries and exponential backoff
- [x] Add MIME type checking for responses
- [x] Implement JavaScript rendering for dynamic content
- [ ] Handle infinite scrolling and click-to-expand content
- [ ] Add support for concurrent requests
- [ ] Develop incremental scraping system
  - [ ] Implement change detection mechanism (timestamps, checksums)
  - [ ] Develop partial update system for modified content
  - [ ] Design efficient storage system for easy updates and comparisons
  - [ ] Implement smart crawling to prioritize frequently updated pages
  - [ ] Develop delta processing to handle only changed content
  - [ ] Implement resumable operations for interrupted scrapes
  - [ ] Set up scheduled runs for automatic updates
- [ ] Implement custom headers (user-agent, etc.)
- [ ] Add cookie handling for session management
- [ ] Implement proxy rotation for large-scale scraping
- [ ] Improve URL normalization
  - [ ] Implement consistent URL format (scheme, domain, path)
  - [ ] Apply case normalization for scheme and domain
  - [ ] Handle default port removal
  - [ ] Implement path normalization
  - [ ] Implement query parameter handling
  - [ ] Remove URL fragments
  - [ ] Establish consistent WWW handling
  - [ ] Implement trailing slash consistency
  - [ ] Resolve protocol-relative URLs
  - [ ] Handle Internationalized Domain Names (IDN)
  - [ ] Implement URL shortener expansion
  - [ ] Remove session IDs from URLs
  - [ ] Recognize and use canonical URLs when specified
- [x] Add content cleaning and normalization functions
- [ ] Implement asset downloading (CSS, JS, images)
- [ ] Add link integrity checking
- [x] Implement structured data extraction
- [ ] Add pagination handling
- [ ] Explore and implement API integration if available

### Additional planned improvements

- Data quality and relevance enhancements
- Time-sensitive data handling
- Data structuring specific to trading information
- Image and chart data extraction
- API integrations for financial data
- Data validation and integrity checks
- Compliance and ethics considerations
- Performance optimizations
- Data preprocessing for financial information
- Metadata enhancements
- Export functionality for machine learning models

For a more detailed view of our roadmap, please see our [TODO.md](TODO.md) file.

## License

This project is open-source and available under the [MIT License](LICENSE).
