"""Play Freeboard! Leverage the web scraping feature in NOAA's Precipitation Frequency Data Server (pfds)

Secondary containment berms complying with SPCC regulations must have an allowance for precipitation.
Looking up different storm events as compiled by NOAA and using that rainfall amount is a good way to
estimate freeboard when designing berms.  Rainfall from 25-yr / 24-hour storm events is customary, but not 
mandatory to comply with the regs.

see: https://www.weather.gov/owp/hdsc_faqs and FAQ 2.5 for more info on web scraping from their data server.

Matt Findley, Findley.Matthew@EPA.gov, EPA Region 8, Enforcement and Compliance Assurance Division, Denver, CO"""

import ast  # python's built in module for "abstract syntax trees", not aboveground storage tanks.
import re  # python's built in module for regular expressions
import click  # external module for building a command line interface
import requests  # external module for http requests.
import pint  # external module for physical quantities with different units of measure.

ureg = pint.UnitRegistry()

# bounding box for the contiguous united states (CONUS)
conus_north = 49.0
conus_south = 24.5
conus_east = -66.9
conus_west = -125.0

# partial list of storm durations available from NOAA's pfds.
# ... not sure we want freeboard for a berm designed around a storm shorter than an 8-hr shift.
duration_choices = (
    "0.5-day",
    "1-day",
    "2-day",
    "3-day",
    "4-day",
    "7-day",
    "10-day",
    "20-day",
    "30-day",
    "45-day",
    "60-day",
)

# ari =  average return interval
ari_choices = (
    "1-yr",
    "2-yr",
    "5-yr",
    "10-yr",
    "25-yr",
    "50-yr",
    "100-yr",
    "200-yr",
    "500-yr",
    "1000-yr",
)


# click really doesn't like arguments that are negative numbers (such as negative longitude values)
# click thinks that -1 is some sort of option that we're trying to invoke, like using a '-h' flag
# setting the ignore_unknown_options to True helps fix this.
@click.command(
    "freeboard",
    context_settings={
        "ignore_unknown_options": True,
        "help_option_names": ("-h", "--help"),
    },
)
@click.version_option("0.1.0", prog_name="freeboard")
@click.argument("lat", type=click.FloatRange(min=conus_south, max=conus_north))
@click.argument("lon", type=click.FloatRange(min=conus_west, max=conus_east))
@click.option(
    "-r",
    "--ari",
    default="25-yr",
    help="average return interval (year)",
    type=click.Choice(ari_choices, case_sensitive=False),
)
@click.option(
    "-d",
    "--duration",
    default="1-day",
    help="storm duration (day)",
    type=click.Choice(duration_choices, case_sensitive=False),
)
@click.option(
    "-u",
    "--units",
    default="inch",
    help="precipitation units (inch or millimeter)",
    type=click.Choice(("inch", "mm"), case_sensitive=False),
)
def cli(lat, lon, ari, duration, units):
    """Look up a location-specific storm event from NOAA's precipitation
    frequency data server.
    Takes location's latitude and longitude as arguments (must be in the contiguous US).
    LAT is the location's latitude (decimal degree)
    LON is the location's longitude (decimal degree, negative values for western hemisphere)
    """

    pfds_results = scrape_precip_data(lat, lon, units)
    storm_event = get_design_storm_event(pfds_results, ari, duration)

    if units == "inch":
        storm_event = storm_event * ureg.inch
    else:
        storm_event = storm_event * ureg.mm

    click.echo(f"Geographic Coordinate: {lat}\u00B0N / {abs(lon)}\u00B0W")
    click.echo(f"Average Return Interval: {ari}")
    click.echo(f"Precipitation Duration: {duration}")
    # click.echo("A Hard Rain's A-Gonna Fall! - Bob Dylan")
    click.echo(f"Storm Event: {storm_event}")


def scrape_precip_data(lat, lon, units):
    """Scrape webpage for precip data based on location.
    Return storm event data as list of lists."""

    # base url, as identified in the NOAA FAQ.
    pfds_url = r"https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/cgi_readH5.py"

    # dictionary with html payload
    scrape_info = {
        "lat": lat,  # decimal degrees
        "lon": lon,  # decimal degrees, negative value for the western hemisphere
        "type": "pf",  # precip frequency, the other option is "rf" for rainfall data.  we want both rain and snow, so pf is best choice.
        "data": "depth",  # NOAA's other option is "intensity"
        "units": None,  # "english" or "metric"
        "series": "pds",  # pds = partial duration series. other option is 'ams' for annual maximum series.  Doesn't make too much different at long return intervals.
    }

    if units == "inch":
        system = "english"
    elif units == "mm":
        system = "metric"
    scrape_info["units"] = system

    try:
        pfds_response = requests.get(
            url=pfds_url, params=scrape_info, timeout=15
        )  # 15-sec timeout
        pfds_response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
    except requests.exceptions.RequestException as err:
        print(f"Error: {err}")

    # ast.literal_eval() is supposed to be a safer way to turn a rando string from the internet into a piece of python code.
    precip_amounts = ast.literal_eval(
        re.search(r"quantiles = (.*);", pfds_response.text).group(1)
    )
    return precip_amounts


def get_design_storm_event(precip_amounts, ari, duration):
    """extract a specific storm event from the precip_amounts list of lists."""
    # rainfall durations and the corresponding index position.
    duration_rows = {
        "5-min": 0,
        "10-min": 1,
        "15-min": 2,
        "30-min": 3,
        "60-min": 4,
        "2-hr": 5,
        "3-hr": 6,
        "6-hr": 7,
        "0.5-day": 8,
        "1-day": 9,
        "2-day": 10,
        "3-day": 11,
        "4-day": 12,
        "7-day": 13,
        "10-day": 14,
        "20-day": 15,
        "30-day": 16,
        "45-day": 17,
        "60-day": 18,
    }

    # average recurrence intervals and the corresponding index position.
    ari_cols = {
        "1-yr": 0,
        "2-yr": 1,
        "5-yr": 2,
        "10-yr": 3,
        "25-yr": 4,
        "50-yr": 5,
        "100-yr": 6,
        "200-yr": 7,
        "500-yr": 8,
        "1000-yr": 9,
    }

    design_storm_event = precip_amounts[duration_rows[duration]][ari_cols[ari]]

    return design_storm_event


if __name__ == "__main__":
    cli()
