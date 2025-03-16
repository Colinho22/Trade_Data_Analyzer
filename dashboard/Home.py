import streamlit as st
from utils.sparql_util import init_fuseki_connection, execute_query

# set page config
st.set_page_config(
    page_title="Trade Data Analyzer",
    page_icon="🌍",
    layout="wide"
)

# initialize Fuseki connection
sparql = init_fuseki_connection()

# define featured organizations list to be used throughout the application
FEATURED_ORG_IDS = [
    "Q458",     # European Union
    "Q7184",    # NATO
    "Q243630",  # BRICS
    "Q19771",   # G20
    "Q1764511", # G7
    "Q181574"   # NAFTA
]

# mapping organization IDs to metadata
ORG_METADATA = {
    "Q458": {"name": "European Union", "emoji": "🇪🇺"},
    "Q7184": {"name": "NATO", "emoji": "🛡️"},
    "Q243630": {"name": "BRICS", "emoji": "🌏"},
    "Q19771": {"name": "G20", "emoji": "💰"},
    "Q1764511": {"name": "G7", "emoji": "🏛️"},
    "Q181574": {"name": "NAFTA", "emoji": "🇨🇦🇺🇸🇲🇽"}
}


def main():
    st.title("🌍 Trade Data Analyzer")

    # introduction section
    st.markdown("""
    Welcome to the Trade Data Analyzer!
    This application allows you to discover global trade patterns from multiple perspectives:

    1. **Country Analysis**: Explore individual country trade patterns, partners, and sociodemographic indicators
    2. **Organization Analysis**: Analyze trade patterns of international organizations like the EU, NATO, BRICS, etc.
    3. **Organization Comparison**: Compare trade relationships between different organizations

    Select one of the options from the sidebar to begin your analysis.
    """)

    # display overview stats
    st.divider()
    st.subheader("About the Data")

    col1, col2, col3, col4 = st.columns(4)

    # count countries
    country_count_query = """
    PREFIX : <http://example.org/country-data#>
    SELECT (COUNT(DISTINCT ?country) AS ?count)
    WHERE {
        ?country a :Country .
    }
    """
    country_count = execute_query(sparql, country_count_query)
    count = int(country_count[0]['count']['value']) if country_count else 0
    col1.metric("Countries", count)

    # count organizations
    org_count_query = """
    PREFIX : <http://example.org/country-data#>
    SELECT (COUNT(DISTINCT ?org) AS ?count)
    WHERE {
        ?org a :Organization .
    }
    """
    org_count = execute_query(sparql, org_count_query)
    count = int(org_count[0]['count']['value']) if org_count else 0
    col2.metric("Organizations", count)

    # count years of trade data from UN Comtrade
    year_count_query = """
    PREFIX : <http://example.org/country-data#>
    SELECT (COUNT(DISTINCT ?year) AS ?count)
    WHERE {
        ?entity :hasTradeAggregate ?measurement .
        ?measurement :year ?year .
    }
    """
    year_count = execute_query(sparql, year_count_query)
    count = int(year_count[0]['count']['value']) if year_count else 0
    col3.metric("Years of Trade Data", count)

    # count trade relationships
    trade_count_query = """
    PREFIX : <http://example.org/country-data#>
    SELECT (COUNT(?measurement) AS ?count)
    WHERE {
        ?country :hasTradeMeasurement ?measurement .
    }
    """
    trade_count = execute_query(sparql, trade_count_query)
    count = int(trade_count[0]['count']['value']) if trade_count else 0
    count_formatted = f"{count:,}"
    col4.metric("Trade Relationships", count_formatted)

    st.markdown("""
       This dashboard uses data from the [UN Comtrade database](https://comtradeplus.un.org/) which is based on the self reported trade activities (import and export) from a country. 
       Additionally, sociodemographic data from [Wikidata](https://www.wikidata.org/) is available to better interpret a country's development over time.
       Not all countries have reportings for every year available. For UN Comtrade this could be because of no trade was reported due to national crises (i.e. civil wars) or political differences with the United Nations.
       Furthermore, the UN Comtrade data can vary from a country's own reported total trade as usually "secret" trades etc. are filtered by nations before reporting their activities to the United Nations.
       The sociodemographic data can also vary in detail. This is due to the difference in dataquality per category and country on Wikidata. There are more reliable sources for the individual indicators.
       As this was not the focus of the project, the convenience of Wikidata was chosen.
       """)

    # featured organizations section
    st.divider()
    st.subheader("Featured Organizations")

    # create a list of featured org details using the metadata map
    featured_orgs = [
        {"id": org_id, "name": ORG_METADATA[org_id]["name"], "emoji": ORG_METADATA[org_id]["emoji"]}
        for org_id in FEATURED_ORG_IDS if org_id in ORG_METADATA
    ]

    # create three columns
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    # display featured organizations in cards
    for i, org in enumerate(featured_orgs):
        col = cols[i % 3]
        with col:
            with st.container(border=True):
                st.markdown(f"### {org['emoji']} {org['name']}")

                # fetch member count
                member_query = f"""
                PREFIX : <http://example.org/country-data#>
                SELECT (COUNT(DISTINCT ?country) AS ?count)
                WHERE {{
                    ?org a :Organization ;
                         :orgId "{org['id']}" .
                    ?country a :Country ;
                            :isMemberOf ?org .
                }}
                """
                member_count = execute_query(sparql, member_query)
                count = int(member_count[0]['count']['value']) if member_count else 0

                # fetch trade volume
                trade_query = f"""
                PREFIX : <http://example.org/country-data#>
                SELECT ?totalExport ?totalImport
                WHERE {{
                    ?org a :Organization ;
                         :orgId "{org['id']}" ;
                         :hasTradeAggregate ?measurement .
                    ?measurement :year ?year ;
                                 :totalExportValue ?totalExport ;
                                 :totalImportValue ?totalImport .
                    {{
                        SELECT ?org (MAX(?year) as ?maxYear)
                        WHERE {{
                            ?org :orgId "{org['id']}" ;
                                 :hasTradeAggregate ?m .
                            ?m :year ?year .
                        }}
                    }}
                    FILTER(?year = ?maxYear)
                }}
                """
                trade_data = execute_query(sparql, trade_query)

                if trade_data:
                    total_export = float(trade_data[0]['totalExport']['value'])
                    total_import = float(trade_data[0]['totalImport']['value'])
                    total_trade = total_export + total_import

                    if total_trade >= 1_000_000_000_000:
                        trade_formatted = f"${total_trade / 1_000_000_000_000:.2f}T"
                    else:
                        trade_formatted = f"${total_trade / 1_000_000_000:.2f}B"
                else:
                    trade_formatted = "N/A"

                st.markdown(f"**Members:** {count}")
                st.markdown(f"**Annual Trade Volume:** {trade_formatted}")

                # add button to navigate to organization page
                button_key = f"view_{org['id']}"
                st.page_link("pages/2_Organization_Analysis.py",
                             label=f"Analyze {org['name']}",
                             icon="📊",
                             use_container_width=True)


if __name__ == "__main__":
    main()