import requests
import json
import pandas as pd
import numpy as np
from pandas import json_normalize
from datetime import datetime, timedelta
from helper_functions import *
from dotenv import load_dotenv
import os


# Base URL for API requests
url = "https://auto.dev/api/listings"

load_dotenv()
AutoDevAPI = os.getenv("AutoDevAPI")
# General parameters for car search
params = {
    'apikey': AutoDevAPI,
    'sort_filter': 'created_at:desc',
    'year_min': 2016,
    'make': 'Toyota',
    'model': 'Camry',
    #'city': 'Boston',
    #'state': 'MA',
    #'location': 'Boston, MA',
    'longitude': -71.058884,
    'latitude': 42.360081,
    'radius': 150,
    'transmission[]': 'automatic',
    'exclude_no_price': 'true'
    # Remove or properly set empty parameters
}

# Call gather_data function to call the API and return a df with the resulting cars
df = gather_data(url,params)

# Pull out relevant columns
X = df[['year', 'mileageUnformatted', 'priceUnformatted', 'trim', 'vin', 'dealerName', 'city', 'createdAt']]
X = X.dropna()


# Filter out unconsidered trims
possible_trims = ['LE', 'SE', 'XLE', 'XSE']
X_mod = X[X['trim'].isin(possible_trims)]

# Estimate prices for each car using the regression model
X_mod['estimate_price'] = X_mod.apply(calculate_price, axis=1)
X_mod['discount'] = X_mod['estimate_price'] - X_mod['priceUnformatted']
X_mod_sorted = X_mod.sort_values(by='discount', ascending=False)

# Save the result as a csv
X_mod_sorted.to_csv('data/newest_data.csv', index=False)

# Call update_daily function to store data about car listings in a given day.
update_master_and_stats(X_mod_sorted)

# Update the latest logs using the Master sheet
update_latest_logs()
    