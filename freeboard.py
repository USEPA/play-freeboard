"""Play Freeboard! Leverage the web scraping feature in NOAA's Precipitation Frequency Data Server (pfds)

Secondary containment berms complying with SPCC regulations must have an allowance for precipitation.
Looking up different storm events as compiled by NOAA and using that rainfall amount is a good way to
estimate freeboard when designing berms.  Rainfall from 25-yr / 24-hour storm events is customary, but not 
mandatory to comply with the regs.

see: https://www.weather.gov/owp/hdsc_faqs and FAQ 2.5 for more info on web scraping from their data server.

Matt Findley, Findley.Matthew@EPA.gov, EPA Region 8, Enforcement and Compliance Assurance Division, Denver, CO"""

import ast  # python's built in module for "abstract syntax trees", not aboveground storage tanks.
import re  # python's built in module for regular expressions
import requests  # external module for http requests.

def scrape_precip_data(lat, lon):
    """Scrape webpage for precip data based on location.
    Return 25-yr / 24-hr stormevent (inches precip)."""

    # base url, as identified in the NOAA FAQ.
    pfds_url = r"https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/cgi_readH5.py"

    #dictionary with html payload 
    scrape_info = {
        "lat": lat,  # decimal degrees
        "lon": lon,  # decimal degrees, negative value for the western hemisphere
        "type": "pf",  # precip frequency, the other option is "rf" for rainfall data.  we want both rain and snow.
        "data": "depth",  # NOAA's other option is "intensity"
        "units": "english",  # NOAA's other option is "metric"
        "series": "pds",  # pds stands for partial duration series, the other option is 'ams' for annual maximum series.  Doesn't make too much different at long return intervals.
    }

    try:
        pfds_response = requests.get(url=pfds_url, params=scrape_info, timeout=15) # 15-sec timeout
        pfds_response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f'HTTP Error: {err}')
    except requests.exceptions.RequestException as err:
        print(f'Error: {err}')

    # ast.literal_eval() is supposed to be a safer way to turn a rando string from the internet into a piece of python code.
    precip_amounts = ast.literal_eval(
        re.search(r"quantiles = (.*);", pfds_response.text).group(1)
    )
    # rainfall durations
    durations = {"5-min": 0,
                 "10-min": 1,
                 "15-min": 2,
                 "30-min": 3,
                 "60-min": 4,
                 "2-hr": 5,
                 "3-hr": 6,
                 "6-hr": 7,
                 "12-hr": 8,
                 "24-hr": 9,
                 "2-day": 10,
                 "3-day": 11,
                 "4-day": 12,
                 "7-day": 13, 
                 "10-day": 14,
                 "20-day": 15,
                 "30-day": 16,
                 "45-day": 17,
                 "60-day": 18,}

    # ari = average recurrence intervals, years
    ari = {"1-yr": 0,
           "2-yr": 1,
           "5-yr": 2,
           "10-yr": 3,
           "25-yr": 4,
           "50-yr": 5,
           "100-yr": 6,
           "200-yr": 7,
           "500-yr": 8,
           "1000-yr": 9}

    design_storm_event = precip_amounts[durations["24-hr"]][ari["25-yr"]]

    return design_storm_event

if __name__ == '__main__':
    lat, lon = 39.7205, -105.1193 # Fed Center, Lakewood, CO
    hard_rain = scrape_precip_data(lat=lat, lon=lon)
    print("A Hard Rain's A-Gonna Fall!")
    print(f"At {lat}\u00B0 latitude and {lon}\u00B0 longitude, a 25-yr / 24-hr storm event is \u2248{hard_rain} inches of precipitation.") 
