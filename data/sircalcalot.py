from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD
import time
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
import threading

#thread-safe printing
print_lock = threading.Lock()


def safe_print(message):
    with print_lock:
        print(message)


#disable SSL verification for local development
def disable_ssl_verification():
    ssl._create_default_https_context = ssl._create_unverified_context


#init and load RDF graph
def init_graph(input_file: str) -> tuple:
    print("Loading TTL file...")
    g = Graph()
    g.parse(input_file, format="turtle")

    #define namespaces
    base = Namespace("http://example.org/country-data#")
    g.bind("base", base)

    print(f"Loaded {len(g)} triples")
    return g, base


#get list of all available countries
def get_countries(g: Graph, base: Namespace) -> list:
    countries = []
    for s, p, o in g.triples((None, RDF.type, base.Country)):
        for _, _, iso in g.triples((s, base.isoCode, None)):
            countries.append((str(s), str(iso)))
    return sorted(countries, key=lambda x: x[1])


#calculate trade totals for a specific country for every year available
def calculate_year_totals(g: Graph, base: Namespace, country_uri: str, year: int) -> dict:
    totals = {
        'goods_export': 0,
        'goods_import': 0,
        'services_export': 0,
        'services_import': 0
    }

    country = URIRef(country_uri)
    year_literal = Literal(year, datatype=XSD.integer)

    #get all trade measurements for the country
    for measurement in g.objects(country, base.hasTradeMeasurement):
        #check measurement type
        types = list(g.objects(measurement, RDF.type))
        if not types:
            continue

        measurement_type = types[0]
        if measurement_type not in [base.GoodsTrade, base.ServicesTrade]:
            continue

        #check year
        measurement_years = list(g.objects(measurement, base.year))
        if not measurement_years or measurement_years[0] != year_literal:
            continue

        #get flow type (import / export) and value
        flow_types = list(g.objects(measurement, base.flowType))
        values = list(g.objects(measurement, base.tradeValue))

        if not flow_types or not values:
            continue

        #process flow type and value
        flow_type = str(flow_types[0])
        try:
            value = float(values[0])
        except (ValueError, TypeError):
            continue

        if value <= 0:
            continue

        #determine key and add value
        trade_type = 'goods' if measurement_type == base.GoodsTrade else 'services'
        direction = 'export' if flow_type == 'Export' else 'import'
        key = f"{trade_type}_{direction}"

        totals[key] += value

    #only return if we have any non-zero values
    if any(value > 0 for value in totals.values()):
        return totals
    return None

    results = g.query(query,
                      initBindings={
                          'target_year': Literal(year, datatype=XSD.integer),
                          'country_uri': URIRef(country_uri)
                      })

    totals = {
        'goods_export': 0,
        'goods_import': 0,
        'services_export': 0,
        'services_import': 0
    }

    for row in results:
        try:
            flow_type = str(row['flowType'])
            measurement_type = str(row['measurementType']).split('#')[-1]
            total_value = float(row['total'].value)

            if total_value > 0:  # Filter non-positive values
                key = f"{'goods' if measurement_type == 'GoodsTrade' else 'services'}_{'export' if flow_type == 'Export' else 'import'}"
                totals[key] = total_value
        except Exception as e:
            safe_print(f"Error processing row: {e}")
            continue

    #only return if we have any non-zero values
    if any(value > 0 for value in totals.values()):
        safe_print(f"Found data for {country_uri} in year {year}: {totals}")
        return totals
    return None


#add trade aggregate measurements to graph
def add_trade_aggregate(g: Graph, base: Namespace, country_uri: str, year: int, totals: dict):
    #create aggregate URI
    aggregate_uri = URIRef(f"{country_uri}_trade_aggregate_{year}")

    #calculate total and balances
    total_export = totals['goods_export'] + totals['services_export']
    total_import = totals['goods_import'] + totals['services_import']

    #add statements as a batch
    statements = [
        (aggregate_uri, RDF.type, base.TradeAggregate),
        (aggregate_uri, base.year, Literal(year, datatype=XSD.integer)),
        (URIRef(country_uri), base.hasTradeAggregate, aggregate_uri),

        #export (flow) values
        (aggregate_uri, base.totalExportValue, Literal(total_export, datatype=XSD.decimal)),
        (aggregate_uri, base.goodsExportValue, Literal(totals['goods_export'], datatype=XSD.decimal)),
        (aggregate_uri, base.servicesExportValue, Literal(totals['services_export'], datatype=XSD.decimal)),

        #import (flow) values
        (aggregate_uri, base.totalImportValue, Literal(total_import, datatype=XSD.decimal)),
        (aggregate_uri, base.goodsImportValue, Literal(totals['goods_import'], datatype=XSD.decimal)),
        (aggregate_uri, base.servicesImportValue, Literal(totals['services_import'], datatype=XSD.decimal)),

        #trade balance values
        (aggregate_uri, base.totalTradeBalance, Literal(total_export - total_import, datatype=XSD.decimal)),
        (aggregate_uri, base.goodsTradeBalance,
         Literal(totals['goods_export'] - totals['goods_import'], datatype=XSD.decimal)),
        (aggregate_uri, base.servicesTradeBalance,
         Literal(totals['services_export'] - totals['services_import'], datatype=XSD.decimal))
    ]

    for statement in statements:
        g.add(statement)


#process a single country with all its years
def process_country(args: Tuple[Graph, Namespace, str, str, List[int]]) -> None:
    g, base, country_uri, iso_code, years = args
    try:
        start_time = time.time()
        safe_print(f"Processing {iso_code}...")

        years_processed = 0
        for year in years:
            totals = calculate_year_totals(g, base, country_uri, year)
            if totals:
                add_trade_aggregate(g, base, country_uri, year, totals)
                years_processed += 1

        duration = time.time() - start_time
        safe_print(f"Completed {iso_code} in {duration:.2f}s - {years_processed} years processed")

    except Exception as e:
        safe_print(f"Error processing {iso_code}: {e}")
        raise


#get years with available trade measurement data
def get_relevant_years(g: Graph, base: Namespace) -> List[int]:
    years = set()

    #get all trade measurements
    for s, p, o in g.triples((None, RDF.type, base.GoodsTrade)):
        for _, _, year in g.triples((s, base.year, None)):
            try:
                years.add(int(year))
            except (ValueError, TypeError):
                continue

    for s, p, o in g.triples((None, RDF.type, base.ServicesTrade)):
        for _, _, year in g.triples((s, base.year, None)):
            try:
                years.add(int(year))
            except (ValueError, TypeError):
                continue

    years_list = sorted(list(years))
    safe_print(f"Found years with trade data: {years_list}")
    return years_list


#execute main function
def main():
    start_time = time.time()

    #initialize
    disable_ssl_verification()
    input_file = "countrydata.ttl"
    output_file = "countrydata_calculated.ttl"

    try:
        #load graph
        g, base = init_graph(input_file)
        print(f"Graph loaded in {time.time() - start_time:.2f}s")

        #get relevant years and countries
        all_years = get_relevant_years(g, base)
        countries = get_countries(g, base)
        total_countries = len(countries)
        print(f"Found {total_countries} countries and {len(all_years)} years with trade data")

        #parallel processing of  countries
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for country_uri, iso_code in countries:
                args = (g, base, country_uri, iso_code, all_years)
                futures.append(executor.submit(process_country, args))

            #wait for all to complete
            for future in as_completed(futures):
                future.result()  #this will raise any exceptions that occurred

        duration = time.time() - start_time
        print(f"\nAll calculations complete in {duration:.2f}s")
        print("Saving enhanced TTL file...")

        g.serialize(destination=output_file, format="turtle")
        print(f"Data saved to {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")
        raise


if __name__ == "__main__":
    main()