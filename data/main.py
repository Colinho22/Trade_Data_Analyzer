from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph, Literal, RDF, URIRef, Namespace, BNode
from rdflib.namespace import RDFS, XSD, OWL, DC
import time
from datetime import datetime
from wikidata_queries import WikidataQueries
import ssl
import csv
from collections import defaultdict
import re


#disable SSL verification for local development
def disable_ssl_verification():
    ssl._create_default_https_context = ssl._create_unverified_context


#initialize wikidata SPARQL endpoint
def init_sparql_endpoint():
    endpoint = SPARQLWrapper("https://query.wikidata.org/sparql")
    endpoint.setReturnFormat(JSON)
    return endpoint


#execute SPARQL queries
def execute_query(endpoint, query):
    endpoint.setQuery(query)
    try:
        results = endpoint.query().convert()
        return results['results']['bindings']
    except Exception as e:
        print(f"Error executing query: {e}")
        return []


#initialize RDF graph with namespaces
def init_graph():
    g = Graph()

    #define namespaces
    base = Namespace("http://example.org/country-data#")
    g.bind("", base)
    g.bind("owl", OWL)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("dc", DC)

    #add ontology declaration
    ontology_uri = URIRef("http://example.org/country-data")
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, DC.title, Literal("Country Data Ontology", lang="en")))
    g.add((ontology_uri, DC.description,
           Literal("An ontology for representing country data including economic and social indicators", lang="en")))
    g.add((ontology_uri, DC.creator, Literal("Generated for Country Data Project", lang="en")))
    g.add((ontology_uri, OWL.versionInfo, Literal("1.0", lang="en")))
    g.add((ontology_uri, DC.date, Literal(datetime.now().strftime("%Y-%m-%d"), datatype=XSD.date)))

    return g, base


#add class definitions
def add_class_definitions(g, base):
    classes = {
        "Entity": "Base class for all entities in the ontology",
        "Country": "A sovereign state",
        "Organization": "An international organization",
        "WorldAggregate": "Special entity representing global trade aggregates",
        "Measurement": "A measurement of an indicator at a specific time",
        "EconomicMeasurement": "Economic indicators like GDP",
        "SocialMeasurement": "Social indicators like HDI",
        "DemographicMeasurement": "Demographic indicators like Population",
        "TradeMeasurement": "Measurement of trade flows between countries",
        "GoodsTrade": "Measurement of trade in physical goods (type code C)",
        "ServicesTrade": "Measurement of trade in services (type code S)"
    }

    for class_name, description in classes.items():
        class_uri = base[class_name]
        g.add((class_uri, RDF.type, OWL.Class))
        g.add((class_uri, RDFS.label, Literal(class_name, lang="en")))
        g.add((class_uri, RDFS.comment, Literal(description, lang="en")))


#add country data to graph
def add_country_data(g, base, country_data):
    #add world aggregate W00
    world_uri = URIRef(f"{base}W00")
    g.add((world_uri, RDF.type, OWL.NamedIndividual))
    g.add((world_uri, RDF.type, base.WorldAggregate))
    g.add((world_uri, base.name, Literal("World", lang="en")))
    g.add((world_uri, base.unCode, Literal("0")))
    g.add((world_uri, base.isoCode, Literal("W00")))

    #add countries
    for country in country_data:
        country_uri = URIRef(f"{base}{country['isoCode']['value']}")
        g.add((country_uri, RDF.type, OWL.NamedIndividual))
        g.add((country_uri, RDF.type, base.Country))
        g.add((country_uri, base.name, Literal(country['countryLabel']['value'])))
        g.add((country_uri, base.isoCode, Literal(country['isoCode']['value'])))


#add measurement data to graph
def add_measurement_data(g, base, data, measurement_type, value_property):
    for item in data:
        country_uri = URIRef(f"{base}{item['isoCode']['value']}")
        measurement_uri = URIRef(f"{base}{item['isoCode']['value']}_{measurement_type}_{item['year']['value']}")

        # add measurement node
        g.add((measurement_uri, RDF.type, OWL.NamedIndividual))
        g.add((measurement_uri, RDF.type, base[measurement_type]))
        g.add((measurement_uri, base.year, Literal(int(item['year']['value']), datatype=XSD.integer)))
        g.add((measurement_uri, base[value_property],
               Literal(float(item[value_property[:-5]]['value']), datatype=XSD.decimal)))

        # link country to measurement
        g.add((country_uri, base[f"has{measurement_type}"], measurement_uri))


#add organization membership data
def add_membership_data(g, base, membership_data):
    for item in membership_data:
        country_uri = URIRef(f"{base}{item['isoCode']['value']}")
        org_uri = URIRef(f"{base}org_{item['org']['value'].split('/')[-1]}")

        # add organization
        g.add((org_uri, RDF.type, OWL.NamedIndividual))
        g.add((org_uri, RDF.type, base.Organization))
        g.add((org_uri, base.name, Literal(item['orgLabel']['value'])))

        # add membership relation
        g.add((country_uri, base.isMemberOf, org_uri))


#check for world aggregate W00
def is_world_aggregate(code):
    world_codes = {'0', 'W00', 'WLD', 'WORLD'}
    return code in world_codes


#load UN Comtrade CSV
def load_comtrade_csv(filename):
    error_summary = defaultdict(int)
    trade_data = []

    #check for encoding
    encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']

    for encoding in encodings:
        try:
            with open(filename, 'r', encoding=encoding) as file:
                reader = csv.DictReader(file)

                for row in reader:
                    try:
                        #validate required fields
                        required_fields = ['typeCode', 'period', 'reporterISO',
                                           'partnerISO', 'flowDesc', 'primaryValue']

                        if not all(field in row for field in required_fields):
                            error_summary['missing_required_fields'] += 1
                            continue

                        #handle world aggregates W00
                        reporter_is_world = is_world_aggregate(row['reporterISO'])
                        partner_is_world = is_world_aggregate(row['partnerISO'])

                        #skip if both reporter and partner are world aggregates W00
                        if reporter_is_world and partner_is_world:
                            error_summary['world_aggregate_pair'] += 1
                            continue

                        #standardize world W00
                        if reporter_is_world:
                            row['reporterISO'] = 'W00'
                        if partner_is_world:
                            row['partnerISO'] = 'W00'

                        #validate and convert numeric fields
                        try:
                            row['primaryValue'] = float(row['primaryValue'])
                            row['period'] = int(row['period'])
                        except ValueError:
                            error_summary['invalid_numeric_value'] += 1
                            continue

                        #validate trade type
                        if row['typeCode'] not in ['C', 'S']:
                            error_summary['invalid_trade_type'] += 1
                            continue

                        #add valid record
                        trade_data.append(row)

                    except Exception as e:
                        error_summary['other_validation_errors'] += 1

                print(f"Successfully loaded file using {encoding} encoding")
                return trade_data, dict(error_summary)

        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Error reading file with {encoding} encoding: {e}")
            continue

    raise ValueError(f"Could not read file {filename} with any of the attempted encodings")

#sanatize text for URI
def sanitize_for_uri(text):
    if not text:
        return "unknown"

    #replace any non-alphanumeric characters
    sanitized = re.sub(r'[^a-zA-Z0-9]', '_', str(text))
    #remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    #remove leading or trailing underscores
    sanitized = sanitized.strip('_')
    #ensure URI starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'n' + sanitized
    return sanitized if sanitized else "unknown"


#add trade measurement to graph
def process_trade_measurement(g, base, reporter_iso, partner_iso, year, value, flow_type, trade_type):
    #skip if invalid codes
    if not reporter_iso or not partner_iso:
        return

    #sanitize all URI components
    safe_reporter = sanitize_for_uri(reporter_iso)
    safe_partner = sanitize_for_uri(partner_iso)
    safe_year = sanitize_for_uri(year)
    safe_flow = sanitize_for_uri(flow_type)
    safe_type = sanitize_for_uri(trade_type)

    #create unique identifier for trade measurement
    measurement_id = f"{safe_reporter}_{safe_partner}_{safe_year}_{safe_flow}_{safe_type}"
    measurement_uri = URIRef(f"{base}{measurement_id}")
    reporter_uri = URIRef(f"{base}{safe_reporter}")
    partner_uri = URIRef(f"{base}{safe_partner}")

    #determine measurement class based on trade type (C = Goods, S = Service --> only C & S allowed by 'def load_comtrade_csv')
    measurement_class = base.GoodsTrade if trade_type == 'C' else base.ServicesTrade

    try:
        #add basic measurement information
        g.add((measurement_uri, RDF.type, OWL.NamedIndividual))
        g.add((measurement_uri, RDF.type, measurement_class))
        g.add((measurement_uri, base.year, Literal(int(year), datatype=XSD.integer)))
        g.add((measurement_uri, base.tradeValue, Literal(float(value), datatype=XSD.decimal)))
        g.add((measurement_uri, base.flowType, Literal(flow_type)))
        g.add((measurement_uri, base.tradeType, Literal(trade_type)))

        #link to reporter and partner entities
        g.add((reporter_uri, base.hasTradeMeasurement, measurement_uri))
        g.add((measurement_uri, base.hasPartnerCountry, partner_uri))

    except Exception as e:
        print(f"Error adding trade measurement to graph: {e}")


#process trade data and add to graph
def add_trade_data(g, base, trade_data):
    for record in trade_data:
        try:
            process_trade_measurement(
                g=g,
                base=base,
                reporter_iso=record['reporterISO'],
                partner_iso=record['partnerISO'],
                year=record['period'],
                value=float(record['primaryValue']),
                flow_type='Import' if 'Import' in record['flowDesc'] else 'Export',
                trade_type=record['typeCode']
            )
        except (ValueError, KeyError) as e:
            print(f"Error processing trade record: {e}")
            continue


#print parsing errors
def print_error_summary(error_summary):
    print("\nUN Comtrade Data Import Summary:")
    print("-" * 50)

    if not error_summary:
        print("No errors encountered during import")
        return

    for category, count in error_summary.items():
        #convert category from snake- to title-case
        display_category = " ".join(word.capitalize() for word in category.split('_'))
        print(f"{display_category}: {count}")
    print("-" * 50)


def main():
    #disable SSL verification
    disable_ssl_verification()

    #initialize SPARQL endpoint and graph
    endpoint = init_sparql_endpoint()
    g, base = init_graph()

    #add class definitions
    add_class_definitions(g, base)

    #initialize queries from wikidata_queries.py
    queries = WikidataQueries()

    try:
        #execute queries and add data to graph
        print("Fetching country data...")
        country_data = execute_query(endpoint, queries.get_base_country_query())
        add_country_data(g, base, country_data)
        time.sleep(5)

        print("Fetching GDP data...")
        gdp_data = execute_query(endpoint, queries.get_gdp_query())
        add_measurement_data(g, base, gdp_data, "EconomicMeasurement", "gdpValue")
        time.sleep(5)

        print("Fetching HDI data...")
        hdi_data = execute_query(endpoint, queries.get_hdi_query())
        add_measurement_data(g, base, hdi_data, "SocialMeasurement", "hdiValue")
        time.sleep(5)

        print("Fetching Democracy Index data...")
        democracy_data = execute_query(endpoint, queries.get_democracy_index_query())
        add_measurement_data(g, base, democracy_data, "SocialMeasurement", "democracyIndexValue")
        time.sleep(5)

        print("Fetching Population data...")
        population_data = execute_query(endpoint, queries.get_population_query())
        add_measurement_data(g, base, population_data, "DemographicMeasurement", "populationValue")
        time.sleep(5)

        print("Fetching Organization membership data...")
        membership_data = execute_query(endpoint, queries.get_membership_query())
        add_membership_data(g, base, membership_data)

        #add UN Comtrade data processing
        print("\nProcessing UN Comtrade data...")
        trade_data, error_summary = load_comtrade_csv("uncomtrade.csv")
        print_error_summary(error_summary)
        print(f"\nSuccessfully loaded {len(trade_data)} valid trade records")

        add_trade_data(g, base, trade_data)

        #save the graph to a file "countrydata.ttl"
        output_file = "countrydata.ttl"
        g.serialize(destination=output_file, format="turtle")
        print(f"Data saved to {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")
        raise


if __name__ == "__main__":
    main()