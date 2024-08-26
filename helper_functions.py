from datetime import datetime, timedelta
import math
import requests
import json
from pandas import json_normalize
import pandas as pd
import numpy as np
import os
# Function to gather data from the Auto-Dev API
# Input: Autodev API, parameters for the car
# Output: dataframe of car listings during the last 24 hours
def gather_data(url,params):

    # Each page has 20 entries therefore 50 pages need to be collected
    page = 1
    loop = True
    
    # Get the current time and calculate the time 24 hours ago
    current_time = datetime.now()
    time_24_hours_ago = current_time - timedelta(hours=24)
    
    # Initialize an empty list to store all records
    all_data = []
    
    # Loop over each page, fetch data, and append to the list
    while loop:
        params['page'] = page
        response = requests.get(url, params=params)
        result = response.json()
        
        if 'records' in result:
            # Extend the all_data list with the records from the current page
            all_data.extend(result['records'])
            
            # Get the createdAt value from the last record
            last_record = result['records'][-1]
            created_at_str = last_record['createdAt']
            
            # Parse the createdAt string into a datetime object
            created_at = datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            
            # Compare createdAt to 24 hours ago
            if created_at < time_24_hours_ago:
                print("Found an entry older than 24 hours, stopping the loop.")
                loop = False
            else:
                print(f"Page {page}: All records are within the last 24 hours.")
        else:
            print(f"Warning: 'records' key not found on page {page}")
            loop = False  # Stop the loop if records are not found
    
        page += 1  # Move to the next page
    
    # Normalize the JSON data into a DataFrame
    df = json_normalize(all_data)
    return df

# Function to estimate a price for a given car
# Input: A car entry that has trim, year, mileage and price
# Output: A float estimate of the car price
def calculate_price(entry):
    possible_trims = ['LE', 'SE', 'XLE', 'XSE']
    trim = entry['trim']
    year = entry['year']
    mileage = entry['mileageUnformatted']
    # Initialize a vector of zeros with length 10 (one for each year from 2016 to 2025)
    year_vector = np.zeros(10, dtype=int)
    # Determine the index corresponding to the given year
    year_index = year - 2016
    # Set the indicator for the given year to 1
    year_vector[year_index] = 1
    # Vector of coefficients for each year
    given_vector = np.array([-581.9210, -1336.4137, -172.4891, 261.1740, 56.1576, 
                             -97.4513, -84.2193, -442.8693, -1402.8466, 0])
    # Calculate the dot product
    year_adjustment = np.dot(year_vector, given_vector) 
    year_adjustment = year_adjustment - 5758.6783 * math.log(2026-year)

    trim_vector = np.zeros(4, dtype=int)
    
    # Determine the index corresponding to the given trim
    trim_index = possible_trims.index(trim)
    
    # Set the indicator for the given trim to 1
    trim_vector[trim_index] = 1
    given_vector = np.array([0, 587.9670, 3688.9185, 4641.6052])
    trim_adjustment = np.dot(trim_vector, given_vector)

    mileage_adjustment = -0.0689 * mileage

    final_price = 34930 + year_adjustment + trim_adjustment + mileage_adjustment
    return final_price

# Function to update the daily log of listing statistics
def update_daily(X_mod_sorted):
    # Convert the date column to be in a desirable format
    X_mod_sorted['createdAt'] = pd.to_datetime(X_mod_sorted['createdAt'], format="%Y-%m-%dT%H:%M:%S.%fZ")
    X_mod_sorted['date'] = X_mod_sorted['createdAt'].dt.date

    # Get date objects for today and yesterday
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    # Only pull yesterday's cars
    X_filtered = X_mod_sorted[X_mod_sorted['date'] == yesterday]
    
    # Calculate the average of the 'discount' column and the sample size for the filtered data
    average_discount = X_filtered['discount'].sum()
    number_listings = len(X_filtered)

    # Save data in this file
    file_path = 'daily_data.csv'
    # Check if the CSV file already exists
    if not os.path.exists(file_path):
        # Create a blank DataFrame with the desired structure
        daily = pd.DataFrame(columns=['date', 'number_of_listings', 'average_discount'])
        
        # Save the blank DataFrame to a CSV file
        daily.to_csv(file_path, index=False)
    else:
        # Load the existing CSV file
        daily = pd.read_csv(file_path)
    
    # Create an entry to save in the log
    new_entry = pd.DataFrame([{
        'date': today,
        'number_of_listings': number_listings,  # Replace with the actual count
        'average_discount': average_discount  # Replace with the actual average discount
    }])
    
    # Concat the new entry to the DataFrame
    daily = pd.concat([daily, new_entry], ignore_index=True)
    
    # Save the updated DataFrame back to the CSV file
    daily.to_csv(file_path, index=False)