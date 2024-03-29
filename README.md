# LangChain API Documentation Scraper

This project is a web scraper designed to download the HTML content of the LangChain API documentation from the base URL `https://api.python.langchain.com/en/latest/langchain_api_reference.html`. The scraper follows links within the specified domain and path, excluding media files, and saves the downloaded HTML files to a local directory structure mirroring the URL structure.

## Features

- Scrapes HTML content from the LangChain API documentation site
- Follows internal links within the specified domain and path
- Excludes media files (PNG, JPG, JPEG, GIF, PDF)
- Saves downloaded HTML files to a local directory structure
- Implements a delay between requests to avoid overloading the server
- Logs scraping activity and errors to a file named `app.log`

## Usage

1. Clone the repository.
2. Install the required dependencies by running `pip install -r requirements.txt`.
3. Run the scraper by executing `python main.py`.

The scraper will start downloading the HTML content from the base URL and save the files to the `downloaded_html` directory. The scraping progress and any errors will be logged in the `app.log` file.

- `downloaded_html/`: Directory where the downloaded HTML files will be saved
- `logger.py`: Module for setting up logging
- `main.py`: Main script to start the scraping process
- `requirements.txt`: List of required Python packages
- `scraper.py`: Module containing the core scraping functions

## Dependencies

- requests
- beautifulsoup4

## License

This project is open-source and available under the [MIT License](LICENSE).