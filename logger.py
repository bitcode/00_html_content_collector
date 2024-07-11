import logging

def setup_logging():
    logging.basicConfig(
        filename='app.log',
        level=logging.DEBUG,  # Set logging level to DEBUG
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)  # Add console output
