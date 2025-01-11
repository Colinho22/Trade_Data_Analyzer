import streamlit as st
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd
import plotly.express as px

#set page config
st.set_page_config(
    page_title="Trade Data Analysis",
    page_icon="🌍",
    layout="wide"
)


#initialize Fuseki connection
@st.cache_resource
def init_fuseki_connection():
    sparql = SPARQLWrapper("http://localhost:3030/countrydata_calculated/query")
    sparql.setReturnFormat(JSON)
    return sparql


#execute SPARQL query with error handling
def execute_query(sparql, query):
    sparql.setQuery(query)
    try:
        results = sparql.query().convert()
        return results['results']['bindings']
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return []


#format large numbers so they are better to display as key number
def format_number(number):
    #store if number is negative
    is_negative = number < 0
    #work with absolute value
    abs_number = abs(number)

    #format based on magnitude (billions, millions and thousands)
    if abs_number >= 1_000_000_000:
        formatted = f"{abs_number / 1_000_000_000:.2f}B"
    elif abs_number >= 1_000_000:
        formatted = f"{abs_number / 1_000_000:.2f}M"
    elif abs_number >= 1_000:
        formatted = f"{abs_number / 1_000:.2f}K"
    else:
        formatted = f"{abs_number:.2f}"

    #add negative sign '-'
    return f"-{formatted}" if is_negative else formatted


#get country options with ISO codes
def get_country_options(sparql):
    country_query = """
    PREFIX : <http://example.org/country-data#>
    SELECT DISTINCT ?countryName ?isoCode
    WHERE {
        ?country a :Country ;
                :name ?countryName ;
                :isoCode ?isoCode .
    }
    ORDER BY ?countryName
    """

    results = execute_query(sparql, country_query)
    if results:
        return [(f"{r['countryName']['value']} ({r['isoCode']['value']})",
                 r['isoCode']['value'],
                 r['countryName']['value']) for r in results]
    return []


#get trade data for a specific country and year
def get_trade_data(sparql, iso_code, year):
    trade_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?totalBalance ?totalExport ?totalImport 
           ?goodsExport ?goodsImport ?servicesExport ?servicesImport
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeAggregate ?measurement .
        ?measurement :year {year} ;
                     :totalTradeBalance ?totalBalance ;
                     :totalExportValue ?totalExport ;
                     :totalImportValue ?totalImport ;
                     :goodsExportValue ?goodsExport ;
                     :goodsImportValue ?goodsImport ;
                     :servicesExportValue ?servicesExport ;
                     :servicesImportValue ?servicesImport .
    }}
    """
    return execute_query(sparql, trade_query)


#show country selector in sidebar
def show_country_selector(sparql):
    st.sidebar.title("Country Selection")
    country_options = get_country_options(sparql)

    search_term = st.sidebar.text_input("Search by Country Name or ISO Code", "").strip().upper()

    if search_term:
        filtered_options = [
            opt for opt in country_options
            if search_term in opt[0].upper() or search_term in opt[1].upper()
        ]
    else:
        filtered_options = country_options

    if filtered_options:
        selected_display = st.sidebar.selectbox(
            "Select Country",
            options=[opt[0] for opt in filtered_options],
            key="country_selector"  # Add a key for proper rerendering
        )

        selected_info = next(opt for opt in filtered_options if opt[0] == selected_display)
        st.session_state.selected_iso = selected_info[1]
        st.session_state.selected_country = selected_info[2]
        return selected_info[1], selected_info[2]

    return None, None


#show trade overview
def get_country_trade_data(sparql, iso_code, year):
    #get current and previous trade data for selected country
    trade_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?year ?totalBalance ?totalExport ?totalImport 
           ?goodsExport ?goodsImport ?servicesExport ?servicesImport
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeAggregate ?measurement .
        ?measurement :year ?year ;
                     :totalTradeBalance ?totalBalance ;
                     :totalExportValue ?totalExport ;
                     :totalImportValue ?totalImport ;
                     :goodsExportValue ?goodsExport ;
                     :goodsImportValue ?goodsImport ;
                     :servicesExportValue ?servicesExport ;
                     :servicesImportValue ?servicesImport .
        FILTER(?year IN ({year}, {year - 1}))
    }}
    ORDER BY ?year
    """
    return execute_query(sparql, trade_query)


#display trade overview for selected country and year
def show_trade_overview(sparql, iso_code, country_name, selected_year):

    #get data for current and previous year
    trade_results = get_country_trade_data(sparql, iso_code, selected_year)

    if not trade_results:
        st.warning(f"No trade data available for {country_name} in {selected_year}")
        return

    #separate current and previous year data
    if len(trade_results) == 2:
        prev_data = trade_results[0]  # Previous year
        current_data = trade_results[1]  # Current year
    else:
        st.warning(f"Incomplete data available for {country_name}")
        return

    try:
        #create columns for total, export and import
        col1, col2, col3 = st.columns(3)

        #column 1: Trade Total
        with col1:
            st.subheader("Trade Total")
            balance = float(current_data['totalBalance']['value'])
            prev_balance = float(prev_data['totalBalance']['value'])
            balance_color = "green" if balance >= 0 else "red"

            st.markdown(f"**Trade Balance:**")
            st.markdown(
                f"<h2 style='color: {balance_color}'>{format_number(balance)} USD</h2>",
                unsafe_allow_html=True
            )

            #calculate year-over-year changes
            export_change = calculate_yoy_change(
                float(current_data['totalExport']['value']),
                float(prev_data['totalExport']['value'])
            )
            import_change = calculate_yoy_change(
                float(current_data['totalImport']['value']),
                float(prev_data['totalImport']['value'])
            )

            #display metrics with YoY changes
            st.metric(
                "Total Exports",
                f"{format_number(float(current_data['totalExport']['value']))} USD",
                export_change
            )
            st.metric(
                "Total Imports",
                f"{format_number(float(current_data['totalImport']['value']))} USD",
                import_change
            )

        #column 2: Goods Trade
        with col2:
            st.subheader("Goods Trade")
            goods_balance = float(current_data['goodsExport']['value']) - float(current_data['goodsImport']['value'])
            prev_goods_balance = float(prev_data['goodsExport']['value']) - float(prev_data['goodsImport']['value'])
            goods_color = "green" if goods_balance >= 0 else "red"

            st.markdown(f"**Goods Balance:**")
            st.markdown(
                f"<h2 style='color: {goods_color}'>{format_number(goods_balance)} USD</h2>",
                unsafe_allow_html=True
            )

            #calculate changes for goods trade
            goods_export_change = calculate_yoy_change(
                float(current_data['goodsExport']['value']),
                float(prev_data['goodsExport']['value'])
            )
            goods_import_change = calculate_yoy_change(
                float(current_data['goodsImport']['value']),
                float(prev_data['goodsImport']['value'])
            )

            #display metrics with YoY changes
            st.metric(
                "Goods Exports",
                f"{format_number(float(current_data['goodsExport']['value']))} USD",
                goods_export_change
            )
            st.metric(
                "Goods Imports",
                f"{format_number(float(current_data['goodsImport']['value']))} USD",
                goods_import_change
            )

        #column 3: Services Trade
        with col3:
            st.subheader("Services Trade")
            services_balance = float(current_data['servicesExport']['value']) - float(
                current_data['servicesImport']['value'])
            prev_services_balance = float(prev_data['servicesExport']['value']) - float(
                prev_data['servicesImport']['value'])
            services_color = "green" if services_balance >= 0 else "red"

            st.markdown(f"**Services Balance:**")
            st.markdown(
                f"<h2 style='color: {services_color}'>{format_number(services_balance)} USD</h2>",
                unsafe_allow_html=True
            )

            #calculate changes for services trade
            services_export_change = calculate_yoy_change(
                float(current_data['servicesExport']['value']),
                float(prev_data['servicesExport']['value'])
            )
            services_import_change = calculate_yoy_change(
                float(current_data['servicesImport']['value']),
                float(prev_data['servicesImport']['value'])
            )

            #display metrics with YoY changes
            st.metric(
                "Services Exports",
                f"{format_number(float(current_data['servicesExport']['value']))} USD",
                services_export_change
            )
            st.metric(
                "Services Imports",
                f"{format_number(float(current_data['servicesImport']['value']))} USD",
                services_import_change
            )

        #add trade balance trend visualization
        display_trade_trends(sparql, iso_code, country_name, selected_year)

    except Exception as e:
        st.error(f"Error processing trade data: {str(e)}")


#calculate YoY percentage change
def calculate_yoy_change(current_value, previous_value):
    if previous_value != 0:
        change = ((current_value - previous_value) / abs(previous_value)) * 100
        return f"{change:+.1f}%"
    return "N/A"


#display trade balance trends for selected country
def display_trade_trends(sparql, iso_code, country_name, selected_year):
    trend_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?year ?totalBalance ?totalExport ?totalImport
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeAggregate ?measurement .
        ?measurement :year ?year ;
                     :totalTradeBalance ?totalBalance ;
                     :totalExportValue ?totalExport ;
                     :totalImportValue ?totalImport .
        FILTER(?year <= {selected_year} && ?year >= {selected_year - 4})
    }}
    ORDER BY ?year
    """

    trend_results = execute_query(sparql, trend_query)
    if trend_results:
        df = pd.DataFrame([
            {
                'Year': int(float(r['year']['value'])),
                'Trade Balance': float(r['totalBalance']['value']),
                'Exports': float(r['totalExport']['value']),
                'Imports': float(r['totalImport']['value'])
            } for r in trend_results
        ])

        st.subheader("Trade Trends")
        fig = px.line(df,
                      x='Year',
                      y=['Trade Balance', 'Exports', 'Imports'],
                      title=f'Trade Trends for {country_name} (Last 5 Years)')
        st.plotly_chart(fig, use_container_width=True)


#show trade partners overview
def get_trade_partners_data(sparql, iso_code, year=None):
    year_filter = f"?measurement :year {year} ." if year else ""

    partners_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?partnerName ?partnerIso ?year
           (SUM(?exportGoods) as ?goodsExports)
           (SUM(?importGoods) as ?goodsImports)
           (SUM(?exportServices) as ?servicesExports)
           (SUM(?importServices) as ?servicesImports)
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeMeasurement ?measurement .
        ?measurement :hasPartnerCountry ?partner ;
                    :year ?year .
        ?partner :name ?partnerName ;
                :isoCode ?partnerIso .

        {year_filter}

        OPTIONAL {{
            ?measurement :tradeType "C" ;  # Goods
                        :flowType "Export" ;
                        :tradeValue ?exportGoods .
        }}
        OPTIONAL {{
            ?measurement :tradeType "C" ;  # Goods
                        :flowType "Import" ;
                        :tradeValue ?importGoods .
        }}
        OPTIONAL {{
            ?measurement :tradeType "S" ;  # Services
                        :flowType "Export" ;
                        :tradeValue ?exportServices .
        }}
        OPTIONAL {{
            ?measurement :tradeType "S" ;  # Services
                        :flowType "Import" ;
                        :tradeValue ?importServices .
        }}

        FILTER(?partnerIso != "W00")  # Exclude World
    }}
    GROUP BY ?partnerName ?partnerIso ?year
    ORDER BY DESC(?goodsExports)
    """

    return execute_query(sparql, partners_query)


#display trade partner analysis
def show_trade_partners(sparql, iso_code, country_name):
    st.header("Trade Partners Analysis")

    #debug information
    st.write(f"Currently analyzing: {country_name} (ISO: {iso_code})")

    #get available years
    year_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT DISTINCT ?year
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeMeasurement ?measurement .
        ?measurement :year ?year .
    }}
    ORDER BY DESC(?year)
    """

    years = execute_query(sparql, year_query)
    if not years:
        st.warning(f"No trade data available for {country_name}")
        return

    #create year options including "All Years"
    year_options = ["All Years"] + sorted([int(float(year['year']['value']))
                                           for year in years], reverse=True)
    selected_year = st.selectbox("Select Year",
                                 year_options,
                                 key=f"year_select_{iso_code}")  # Unique key per country

    #get trade partner data with explicit country filter
    partners_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?partnerName ?partnerIso ?year
           (SUM(?exportGoods) as ?goodsExports)
           (SUM(?importGoods) as ?goodsImports)
           (SUM(?exportServices) as ?servicesExports)
           (SUM(?importServices) as ?servicesImports)
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeMeasurement ?measurement .
        ?measurement :hasPartnerCountry ?partner ;
                    :year ?year .
        ?partner :name ?partnerName ;
                :isoCode ?partnerIso .

        {f"FILTER(?year = {selected_year})" if selected_year != "All Years" else ""}

        OPTIONAL {{
            ?measurement :tradeType "C" ;
                        :flowType "Export" ;
                        :tradeValue ?exportGoods .
        }}
        OPTIONAL {{
            ?measurement :tradeType "C" ;
                        :flowType "Import" ;
                        :tradeValue ?importGoods .
        }}
        OPTIONAL {{
            ?measurement :tradeType "S" ;
                        :flowType "Export" ;
                        :tradeValue ?exportServices .
        }}
        OPTIONAL {{
            ?measurement :tradeType "S" ;
                        :flowType "Import" ;
                        :tradeValue ?importServices .
        }}

        FILTER(?partnerIso != "W00")
    }}
    GROUP BY ?partnerName ?partnerIso ?year
    """

    trade_data = execute_query(sparql, partners_query)

    #debug the query results
    if not trade_data:
        st.warning(f"No trade partner data found for {country_name}")
        st.write("Debug: Query returned no results")
        return

    #convert to DataFrame with error handling
    try:
        df = pd.DataFrame([
            {
                'Partner': r['partnerName']['value'],
                'Year': int(float(r['year']['value'])),
                'Goods Exports': float(r['goodsExports']['value']) if r.get('goodsExports') else 0,
                'Goods Imports': float(r['goodsImports']['value']) if r.get('goodsImports') else 0,
                'Services Exports': float(r['servicesExports']['value']) if r.get('servicesExports') else 0,
                'Services Imports': float(r['servicesImports']['value']) if r.get('servicesImports') else 0
            } for r in trade_data
        ])

        #calculate totals
        df['Total Exports'] = df['Goods Exports'] + df['Services Exports']
        df['Total Imports'] = df['Goods Imports'] + df['Services Imports']

        #create visualization tabs
        viz_tab1, viz_tab2 = st.tabs(["Export Analysis", "Import Analysis"])

        with viz_tab1:
            st.subheader("Top Export Partners")
            if selected_year == "All Years":
                export_df = df.groupby('Partner').agg({
                    'Goods Exports': 'sum',
                    'Services Exports': 'sum'
                }).reset_index()
            else:
                export_df = df[['Partner', 'Goods Exports', 'Services Exports']]

            export_df['Total Exports'] = export_df['Goods Exports'] + export_df['Services Exports']
            export_df = export_df.nlargest(15, 'Total Exports')

            fig_exports = px.bar(export_df,
                                 x='Partner',
                                 y=['Goods Exports', 'Services Exports'],
                                 title=f'Top 15 Export Partners - {country_name} ({selected_year})',
                                 labels={'value': 'Export Value (USD)',
                                         'variable': 'Export Type'},
                                 barmode='stack')
            st.plotly_chart(fig_exports, use_container_width=True)

        with viz_tab2:
            st.subheader("Top Import Partners")
            if selected_year == "All Years":
                import_df = df.groupby('Partner').agg({
                    'Goods Imports': 'sum',
                    'Services Imports': 'sum'
                }).reset_index()
            else:
                import_df = df[['Partner', 'Goods Imports', 'Services Imports']]

            import_df['Total Imports'] = import_df['Goods Imports'] + import_df['Services Imports']
            import_df = import_df.nlargest(15, 'Total Imports')

            fig_imports = px.bar(import_df,
                                 x='Partner',
                                 y=['Goods Imports', 'Services Imports'],
                                 title=f'Top 15 Import Partners - {country_name} ({selected_year})',
                                 labels={'value': 'Import Value (USD)',
                                         'variable': 'Import Type'},
                                 barmode='stack')
            st.plotly_chart(fig_imports, use_container_width=True)

        #display detailed data table
        st.subheader("Detailed Trade Partner Data")
        if len(df) > 0:
            summary_df = df.copy()
            for col in summary_df.select_dtypes(include=['float64']).columns:
                summary_df[col] = summary_df[col].apply(format_number)
            st.dataframe(summary_df, use_container_width=True)
        else:
            st.info("No detailed data available for the selected filters")

    except Exception as e:
        st.error(f"Error processing trade data: {str(e)}")
        st.write("Debug: Error in data processing", e)


#show sociodemographic indicators
def show_sociodemographic(sparql, iso_code, country_name):
    st.header("Sociodemographic Indicators")

    #query for population and HDI data
    indicators_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?year ?population ?hdi
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" .
        ?country :hasDemographicMeasurement ?dm .
        ?dm :year ?year ;
            :populationValue ?population .
        ?country :hasSocialMeasurement ?sm .
        ?sm :year ?year ;
            :hdiValue ?hdi .
    }}
    ORDER BY ?year
    """

    results = execute_query(sparql, indicators_query)
    if results:
        df = pd.DataFrame([
            {
                'Year': int(float(r['year']['value'])),
                'Population': float(r['population']['value']),
                'HDI': float(r['hdi']['value'])
            } for r in results
        ])

        #latest values as key numbers
        latest = df.iloc[-1]
        col1, col2 = st.columns(2)
        col1.metric("Latest Population Count",
                  format_number(latest['Population']),
                  f"{((df.iloc[-1]['Population'] - df.iloc[-2]['Population']) / df.iloc[-2]['Population'] * 100):.2f}%")
        col2.metric("Latest HDI",
                  f"{latest['HDI']:.3f}",
                  f"{((df.iloc[-1]['HDI'] - df.iloc[-2]['HDI']) / df.iloc[-2]['HDI'] * 100):.2f}%")

        #Population trend
        fig_pop = px.line(df,
                          x='Year',
                          y='Population',
                          title=f'Population Trend - {country_name}')
        st.plotly_chart(fig_pop)

        #HDI trend
        fig_hdi = px.line(df,
                          x='Year',
                          y='HDI',
                          title=f'Human Development Index - {country_name}')
        st.plotly_chart(fig_hdi)


def main():
    st.title("🌍 Trade Data Analysis")
    st.write(
        "This dashboard allows you to explore trade data from 2014-2023 based on the UN Comtrade database. Additionally, some sociodemographic data is available to better interpret a country's development over time.")

    #initialize session state for country selection
    if 'selected_iso' not in st.session_state:
        st.session_state.selected_iso = None
    if 'selected_country' not in st.session_state:
        st.session_state.selected_country = None

    #initialize connection
    sparql = init_fuseki_connection()

    #get selected country info
    selected_iso, selected_country = show_country_selector(sparql)

    if selected_iso and selected_country:
        #main content area with tabs
        tab1, tab2, tab3 = st.tabs(["Trade Overview", "Trade Partners", "Sociodemographics"])

        with tab1:
            st.header("Trade Overview")

            if st.session_state.selected_iso and st.session_state.selected_country:
                year_query = """
                PREFIX : <http://example.org/country-data#>
                SELECT DISTINCT ?year
                WHERE {
                    ?country :hasTradeAggregate ?measurement .
                    ?measurement :year ?year .
                }
                ORDER BY DESC(?year)
                """

                years = execute_query(sparql, year_query)
                if years:
                    years = sorted([int(float(year['year']['value'])) for year in years], reverse=True)
                    selected_year = st.selectbox("Select Year", years, key="year_selector")
                    show_trade_overview(sparql,
                                        st.session_state.selected_iso,
                                        st.session_state.selected_country,
                                        selected_year)
            else:
                st.info("Please select a country from the sidebar to view trade overview.")

        with tab2:
            show_trade_partners(sparql, selected_iso, selected_country)

        with tab3:
            show_sociodemographic(sparql, selected_iso, selected_country)


if __name__ == "__main__":
    main()