import os
from bs4 import BeautifulSoup
import requests
import cairosvg  # Import cairosvg for SVG to PNG conversion
from urllib.parse import urljoin

def fetch_svg_from_iframe(url, base_dir, index):
    response = requests.get(url)
    response.raise_for_status()
    svg_content = response.text

    # Save the SVG content to a temporary file
    svg_file = os.path.join(base_dir, f'temp_{index}.svg')
    with open(svg_file, 'w') as file:
        file.write(svg_content)

    # Convert the SVG to PNG
    png_file = os.path.join(base_dir, f'diagram_{index}.png')
    cairosvg.svg2png(url=svg_file, write_to=png_file)
    os.remove(svg_file)  # Clean up SVG file after conversion

    return png_file

def test_svg_to_png_conversion(url):
    # Directory setup
    base_dir = 'test_output'
    os.makedirs(base_dir, exist_ok=True)

    # Fetch HTML content from the URL
    response = requests.get(url)
    response.raise_for_status()
    html_content = response.text

    # Parse HTML and find iframes pointing to SVGs
    soup = BeautifulSoup(html_content, 'html.parser')
    iframes = soup.find_all('iframe', src=True)
    if not iframes:
        print("No iframes with SVG sources found in the HTML.")
        return

    # Process each iframe containing SVG
    for index, iframe in enumerate(iframes):
        src = iframe['src']
        full_svg_url = urljoin(url, src)
        try:
            png_file = fetch_svg_from_iframe(full_svg_url, base_dir, index)
            # Replace iframe with img tag pointing to the converted PNG
            img_tag = soup.new_tag('img', src=os.path.basename(png_file))  # Only the filename, no folder path

            # Debugging: Print before and after replacement
            print(f"Replacing iframe:\n{iframe}\nWith img tag:\n{img_tag}")

            iframe.replace_with(img_tag)
        except Exception as e:
            print(f"Error processing iframe {src}: {e}")
            continue

    # Save the modified HTML
    output_html_path = os.path.join(base_dir, 'test_output.html')
    with open(output_html_path, 'w', encoding='utf-8') as file:
        file.write(str(soup))

    # Check if the PNG files were created
    png_files = [f for f in os.listdir(base_dir) if f.endswith('.png')]
    assert png_files, "PNG file was not created."

    # Debugging: Print the relevant parts of the modified HTML content
    with open(output_html_path, 'r', encoding='utf-8') as file:
        modified_html_content = file.read()

    # Simplified assertion to check for the presence of the img tag
    for png_file in png_files:
        img_tag = f'<img src="{os.path.basename(png_file)}"/>'
        if img_tag not in modified_html_content:
            print(f"SVG was not replaced by PNG in the HTML for {os.path.basename(png_file)}")
            print(f"Expected img tag:\n{img_tag}\n")
            # Debugging: Print the section of HTML containing the img tag
            start_index = modified_html_content.find('<img src="')
            end_index = modified_html_content.find('>', start_index) + 1
            print(f"Actual HTML around img tag:\n{modified_html_content[start_index:end_index]}\n")
            raise AssertionError("SVG was not replaced by PNG in the HTML.")

    print("Test passed: SVG was successfully converted to PNG and HTML was updated.")

    # Do not delete the output directory
    # shutil.rmtree(base_dir)

# URL to test
test_url = 'https://docs.opencv.org/4.10.0/d4/d32/classcv_1_1__InputArray.html'

# Run the test
if __name__ == "__main__":
    test_svg_to_png_conversion(test_url)
