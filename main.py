import os
from flask import Flask, render_template
import requests
import pandas as pd
from io import StringIO, BytesIO
import threading
import schedule
import time
from datetime import datetime


app = Flask(__name__)

# Dropbox link to the CSV file
DROPBOX_XLSX_URL = os.environ['DROPBOX_XLSX_URL']


# Define a function to fetch data from Dropbox link
def fetch_and_update_data():
    data = fetch_data_from_dropbox()
    app.config['data'] = data


# Schedule the function to run every 3 minutes
schedule.every(3).minutes.do(fetch_and_update_data)


# Define a route to serve the index page
@app.route('/')
def index():
    # Fetch data from Dropbox link initially
    if 'data' not in app.config:
        fetch_and_update_data()

    # Get the data from the app config
    data = app.config['data']
    return render_template('index.html', data=data)


# Run the scheduler in a separate thread
def scheduler_thread():
    while True:
        schedule.run_pending()
        time.sleep(1)


# Start the scheduler thread
scheduler = threading.Thread(target=scheduler_thread)
scheduler.start()


def fetch_data_from_dropbox():
    try:
        # Fetch the Excel file from the Dropbox link
        response = requests.get(DROPBOX_XLSX_URL)
        response.raise_for_status()  # Raise an error if request fails

        # Read Excel file and rename the Unnamed column to something more meaningful
        excel_data = pd.read_excel(BytesIO(response.content))
        # Define a mapping of old column names to new column names
        column_mapping = {
            'Unnamed: 0': 'Type',
            'Unnamed: 1': 'Load Origin',
            'Unnamed: 2': 'Destination',
            'Unnamed: 3': 'Date',
            'Unnamed: 4': 'Notes',
            'Unnamed: 5': 'Miles',
            'Unnamed: 6': 'Rate',
            'Unnamed: 7': 'Material'
        }

        # Rename columns in the DataFrame using the mapping
        excel_data.rename(columns=column_mapping, inplace=True)

        # Drop empty rows
        excel_data.dropna(axis=0, how='all', inplace=True)

        # Convert data to list of dictionaries
        data = excel_data.to_dict(orient='records')

        # Replace "NaN" values with empty strings
        for row in data:
            for key, value in row.items():
                if pd.isna(value):
                    row[key] = ""

        # Convert 'Date' column to datetime format if it's not already in datetime format
        excel_data['Date'] = pd.to_datetime(excel_data['Date'], errors='coerce')

        # Format 'Date' column as MM/DD/YY
        excel_data['Date'] = excel_data['Date'].dt.strftime('%m/%d/%y')

        # Replace "NaT" values (resulting from string conversion errors) with today's date
        today_date = pd.to_datetime('today').strftime('%m/%d/%y')
        excel_data['Date'] = excel_data['Date'].fillna(today_date)

        print(data)
        print(f"refreshed at {datetime.now()}")
        return data
    except Exception as e:
        # Handle any errors that occur during the process
        print(f"Error fetching or parsing data: {e}")
        return []


if __name__ == '__main__':
    app.run(debug=True)
