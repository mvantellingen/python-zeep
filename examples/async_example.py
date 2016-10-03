import asyncio
from lxml import etree
from zeep.client import AsyncClient, AsyncTransport
from zeep.exceptions import Fault


"""Example using AsyncClient to make concurrent requests to the Global Weather service.
Determines how many cities are on record for each country.
Run this example multiple times (noting the order in which Countries appear in the console) to observe concurrency.
"""

def handle_fut(fut):
    # Callback scheduled by add_done_callback - will be called when future is done.
    for resp in fut.result():
        if issubclass(resp.__class__, Fault):
            print(resp)
        else:
            print(parse_response(resp))

def parse_response(resp):
    # Parse the response and return the number of countries on record for the country.
    doc = etree.XML(resp)
    country_name = doc.find('.//Country').text
    no_cities = len(doc.findall('.//City'))
    return '{} has {} cities on record.'.format(country_name, no_cities)
    

if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    
    # Pass asyncio event loop as first parameter to AsyncTransport
    t = AsyncTransport(loop, cache=None)
    c = loop.run_until_complete(AsyncClient.create('http://webservicex.net/globalweather.asmx?wsdl', transport=t))

    # Create a list of tasks to be run concurrently
    tasks = []
    for country in ['United Kingdom', 'Ireland', 'Canada', 'Brazil', 'Germany', 'France', 'Cyprus']:
        tasks.append(c.service.GetCitiesByCountry(CountryName=country))

    # Gather tasks into a Future, return exceptions
    fut = asyncio.gather(*tasks, return_exceptions=True)

    # Schedule a callback for when Future result is set - will be called with the Future as the sole parameter
    fut.add_done_callback(handle_fut)

    loop.run_until_complete(fut)
    loop.run_until_complete(t.session.close())
