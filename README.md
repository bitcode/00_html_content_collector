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

For a complete list of dependencies, refer to the `requirements.txt` file.

## Customization

You can customize the scraper behavior by modifying the following parameters in `main.py`:

- `base_url`: The starting URL for the documentation website
- `delay`: The time delay between requests (default is 3 seconds)

## Logging

The scraper logs its activity to both a file (`app.log`) and the console. You can adjust the logging level in `logger.py` if needed.

## License

This project is open-source and available under the [MIT License](LICENSE).
