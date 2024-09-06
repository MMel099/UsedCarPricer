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

    # Intercept could be interpreted as the price of a new 2025 LE car with no miles
    intercept = 34850
    # Initialize a vector of zeros with length 10 (one for each year from 2016 to 2025)
    year_vector = np.zeros(10, dtype=int)
    # Determine the index corresponding to the given year
    year_index = year - 2016
    # Set the indicator for the given year to 1
    year_vector[year_index] = 1
    # Vector of coefficients for each year
    given_vector = np.array([-1059.3203, -1607.8351, -137.5725, 646.0091,  -168.7158, 
                             202.4573, 214.1618, -189.8995, -1174.5509, 0])
    # Calculate the dot product
    year_adjustment = np.dot(year_vector, given_vector) 
    year_adjustment = year_adjustment - 5703.2751 * math.log(2026-year)

    trim_vector = np.zeros(4, dtype=int)
    
    # Determine the index corresponding to the given trim
    trim_index = possible_trims.index(trim)
    
    # Set the indicator for the given trim to 1
    trim_vector[trim_index] = 1
    given_vector = np.array([0, 757.9916, 3942.0173, 4951.5116])
    trim_adjustment = np.dot(trim_vector, given_vector)

    mileage_adjustment = -0.0666 * mileage

    final_price = intercept + year_adjustment + trim_adjustment + mileage_adjustment
    return final_price

# Function to update the daily log of listing statistics
def update_master_and_stats(X_mod_sorted):
    # Convert the date column to be in a desirable format
    X_mod_sorted['createdAt'] = pd.to_datetime(X_mod_sorted['createdAt'], format="%Y-%m-%dT%H:%M:%S.%fZ").dt.date

    # Get date objects for today and yesterday
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    # Only pull yesterday's cars
    X_filtered = X_mod_sorted[X_mod_sorted['createdAt'] == yesterday]
    
    # Calculate the average of the 'discount' column and the sample size for the filtered data
    average_discount = X_filtered['discount'].mean()
    number_listings = len(X_filtered)

    # Save new cars in a master data sheet
    master_filepath = 'data/master_data.csv'
    if not os.path.exists(master_filepath):
        # Create a blank DataFrame with the desired structure
        master = pd.DataFrame(columns=X_mod_sorted.columns)
        
        # Save the blank DataFrame to a CSV file
        master.to_csv(master_filepath, index=False)
    else:
        # Load the existing CSV file
        master = pd.read_csv(master_filepath)
    master = pd.concat([master, X_filtered], ignore_index=True)
    # Save the updated DataFrame back to the CSV file
    master.to_csv(master_filepath, index=False)
    
    # Save daily stats in this file
    stats_filepath = 'data/daily_stats.csv'
    # Check if the CSV file already exists
    if not os.path.exists(stats_filepath):
        # Create a blank DataFrame with the desired structure
        daily = pd.DataFrame(columns=['date', 'number_of_listings', 'average_discount'])
        
        # Save the blank DataFrame to a CSV file
        daily.to_csv(stats_filepath, index=False)
    else:
        # Load the existing CSV file
        daily = pd.read_csv(stats_filepath)
    
    # Create an entry to save in the log
    new_entry = pd.DataFrame([{
        'date': yesterday,
        'number_of_listings': number_listings,  # Replace with the actual count
        'average_discount': average_discount  # Replace with the actual average discount
    }])
    
    # Concat the new entry to the DataFrame
    daily = pd.concat([daily, new_entry], ignore_index=True)
    
    # Save the updated DataFrame back to the CSV file
    daily.to_csv(stats_filepath, index=False)


# Function to update the daily, weekly and monthly listing logs
def update_latest_logs():
    master_filepath = 'data/master_data.csv'
    # Load the existing CSV master file
    master = pd.read_csv(master_filepath)
    master_mod = master[['createdAt', 'dealerName', 'city', 'year', 'mileageUnformatted', 'trim', 'priceUnformatted', 'discount']]
    master_mod.columns = ['Date', 'Dealer', 'City', 'Model Year', 'Mileage', 'Trim', 'Price', 'Discount']

    thirty_day_filepath = 'data/thirty_day_data.csv'
    # Filter for entries within the last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    thirty_day_log = master_mod[pd.to_datetime(master_mod['Date']) >= thirty_days_ago]
    thirty_day_log = thirty_day_log.sort_values(by='Discount', ascending=False)
    
    # Save the DataFrame to a CSV file
    thirty_day_log.to_csv(thirty_day_filepath, index=False)

    seven_day_filepath = 'data/seven_day_data.csv'
    # Filter for entries within the last 7 days
    seven_days_ago = datetime.now() - timedelta(days=7)
    seven_day_log = master_mod[pd.to_datetime(master_mod['Date']) >= seven_days_ago]
    seven_day_log = seven_day_log.sort_values(by='Discount', ascending=False)
    
    # Save the DataFrame to a CSV file
    seven_day_log.to_csv(seven_day_filepath, index=False)

    one_day_filepath = 'data/one_day_data.csv'
    # Filter for entries within the last 7 days

    
    yesterday = datetime.now() - timedelta(hours=24)
    one_day_log = master_mod[pd.to_datetime(master_mod['Date']) == yesterday]
    one_day_log = one_day_log.sort_values(by='Discount', ascending=False)
    
    # Save the DataFrame to a CSV file
    one_day_log.to_csv(one_day_filepath, index=False)
    