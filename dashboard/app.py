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


#get most recent year for immediate display in trade data overview tab
def get_available_years(sparql, iso_code):
    year_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT DISTINCT ?year
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeAggregate ?measurement .
        ?measurement :year ?year .
    }}
    ORDER BY DESC(?year)
    """

    years = execute_query(sparql, year_query)
    if years:
        available_years = sorted([int(float(year['year']['value']))
                                for year in years], reverse=True)
        most_recent_year = available_years[0]
        return available_years, most_recent_year
    return [], None


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
            key="country_selector"  #add key for rendering
        )

        selected_info = next(opt for opt in filtered_options if opt[0] == selected_display)
        st.session_state.selected_iso = selected_info[1]
        st.session_state.selected_country = selected_info[2]

        #about section
        st.sidebar.divider()
        st.sidebar.subheader("About")
        st.sidebar.markdown(
            "This dashboard allows you to explore trade data from ***2014-2023*** based on the UN Comtrade database. Additionally, some sociodemographic data is available to better interpret a country's development over time.")
        st.sidebar.divider()
        st.sidebar.markdown("by Colinho22  |  👾[GitHub](https://github.com/Colinho22/Trade_Data_Analyzer)")

        return selected_info[1], selected_info[2]

    return None, None


#get current trade data for selected country
def get_country_trade_data(sparql, iso_code, year):
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


#display trade overview for selected country and year (show latest first)
def show_trade_overview(sparql, iso_code, country_name, selected_year=None):
    available_years, most_recent_year = get_available_years(sparql, iso_code)

    if not available_years:
        st.warning(f"No trade data available for {country_name}")
        return

    #if no year is selected, use the most recent year
    if selected_year is None:
        selected_year = most_recent_year

    #show year selector with most recent year as default
    selected_year = st.selectbox(
        "Select Year",
        available_years,
        index=available_years.index(selected_year),
        key="year_selector"
    )

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
        current_data = trade_results[0]  # Only current year available
        prev_data = None

    try:
        #create columns for total, export and import
        col1, col2, col3 = st.columns(3)

        #column 1: Trade Total
        with col1:
            st.subheader("Trade Total")
            balance = float(current_data['totalBalance']['value'])
            balance_color = "green" if balance >= 0 else "red"

            st.markdown(f"**Trade Balance:**")
            st.markdown(
                f"<h2 style='color: {balance_color}'>{format_number(balance)} USD</h2>",
                unsafe_allow_html=True
            )

            #calculate year-over-year changes if previous data exists
            if prev_data:
                export_change = calculate_yoy_change(
                    float(current_data['totalExport']['value']),
                    float(prev_data['totalExport']['value'])
                )
                import_change = calculate_yoy_change(
                    float(current_data['totalImport']['value']),
                    float(prev_data['totalImport']['value'])
                )
            else:
                export_change = None
                import_change = None

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
            goods_color = "green" if goods_balance >= 0 else "red"

            st.markdown(f"**Goods Balance:**")
            st.markdown(
                f"<h2 style='color: {goods_color}'>{format_number(goods_balance)} USD</h2>",
                unsafe_allow_html=True
            )

            #calculate changes for goods trade if previous data exists
            if prev_data:
                goods_export_change = calculate_yoy_change(
                    float(current_data['goodsExport']['value']),
                    float(prev_data['goodsExport']['value'])
                )
                goods_import_change = calculate_yoy_change(
                    float(current_data['goodsImport']['value']),
                    float(prev_data['goodsImport']['value'])
                )
            else:
                goods_export_change = None
                goods_import_change = None

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
            services_color = "green" if services_balance >= 0 else "red"

            st.markdown(f"**Services Balance:**")
            st.markdown(
                f"<h2 style='color: {services_color}'>{format_number(services_balance)} USD</h2>",
                unsafe_allow_html=True
            )

            #calculate changes for services trade if previous data exists
            if prev_data:
                services_export_change = calculate_yoy_change(
                    float(current_data['servicesExport']['value']),
                    float(prev_data['servicesExport']['value'])
                )
                services_import_change = calculate_yoy_change(
                    float(current_data['servicesImport']['value']),
                    float(prev_data['servicesImport']['value'])
                )
            else:
                services_export_change = None
                services_import_change = None

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
    st.divider()

    #query to get all years data
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
    }}
    ORDER BY ?year
    """

    trend_results = execute_query(sparql, trend_query)
    if trend_results:
        #create DataFrame with all trade data
        df = pd.DataFrame([
            {
                'Year': int(float(r['year']['value'])),
                'Trade Balance': float(r['totalBalance']['value']),
                'Exports': float(r['totalExport']['value']),
                'Imports': float(r['totalImport']['value'])
            } for r in trend_results
        ])

        #add data set insights
        col1, col2, col3 = st.columns(3)

        with col1:
            year_count = len(df)
            year_range = f"{df['Year'].min()} - {df['Year'].max()}"
            st.markdown("### Available Trade Data")
            st.write(f"Number of years: {year_count}")
            st.write(f"Time period: {year_range}")

        with col2:
            st.markdown("### Trade Balance Insight")
            avg_balance = df['Trade Balance'].mean()
            balance_color = "green" if avg_balance >= 0 else "red"
            st.markdown(
                f"**Average Trade Balance:** <span style='color:{balance_color}'>{format_number(avg_balance)} USD</span>",
                unsafe_allow_html=True)

        with col3:
            max_year = df.loc[df['Trade Balance'].idxmax(), 'Year']
            min_year = df.loc[df['Trade Balance'].idxmin(), 'Year']
            st.markdown("### Best/Worst Years")
            st.write(f"Best trade balance: {max_year}")
            st.write(f"Worst trade balance: {min_year}")

        st.divider()

        #create bar chart comparing exports and imports
        st.subheader("Trade Trends")

        #reshape data for bar chart
        plot_df = pd.melt(df,
                          id_vars=['Year'],
                          value_vars=['Exports', 'Imports'],
                          var_name='Type',
                          value_name='Value')

        #create bar chart for imports and exports
        fig_trade = px.bar(plot_df,
                           x='Year',
                           y='Value',
                           color='Type',
                           barmode='group',
                           title=f'Trade Trends for {country_name}')

        #update layout for trade chart
        fig_trade.update_layout(
            yaxis_title='Value (USD)',
            xaxis_title='Year',
            hovermode='x unified',
            legend_title='',
            showlegend=True
        )

        #show trade chart
        st.plotly_chart(fig_trade, use_container_width=True)

        #add separator between charts
        st.divider()

        #create line chart for trade balance
        fig_balance = px.line(df,
                              x='Year',
                              y='Trade Balance',
                              title=f'Trade Balance Development for {country_name}')

        #update layout for balance chart
        fig_balance.update_layout(
            yaxis_title='Trade Balance (USD)',
            xaxis_title='Year',
            hovermode='x unified'
        )

        #add zero line reference
        fig_balance.add_hline(y=0,
                              line_dash="dot",
                              line_color="gray",
                              annotation_text="Balance = 0")

        #show balance chart
        st.plotly_chart(fig_balance, use_container_width=True)


#trade partner data query
def partners_get_data(sparql, iso_code, time_period="recent"):
    current_year = 2023  #update based on your data availability

    #define year filter based on time period
    if time_period == "recent":
        year_filter = f"FILTER(?year >= {current_year - 2})"
    elif isinstance(time_period, int):
        year_filter = f"FILTER(?year = {time_period})"
    else:  # "all" time
        year_filter = ""

    partners_query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?partnerName ?partnerIso ?year
           (SUM(IF(?flowType = "Export", ?tradeValue, 0)) as ?exportValue)
           (SUM(IF(?flowType = "Import", ?tradeValue, 0)) as ?importValue)
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :hasTradeMeasurement ?measurement .
        ?measurement :hasPartnerCountry ?partner ;
                    :year ?year ;
                    :tradeValue ?tradeValue ;
                    :flowType ?flowType .
        ?partner :name ?partnerName ;
                :isoCode ?partnerIso .

        {year_filter}
        FILTER(?partnerIso != "W00")  # Exclude World aggregate
    }}
    GROUP BY ?partnerName ?partnerIso ?year
    ORDER BY DESC(?year)
    """

    return execute_query(sparql, partners_query)


#process data into DataFrame
def partners_process_data(raw_data):
    if not raw_data:
        return None

    #create initial DataFrame
    df = pd.DataFrame([{
        'Partner': r['partnerName']['value'],
        'Partner ISO': r['partnerIso']['value'],
        'Year': int(float(r['year']['value'])),
        'Total Exports': float(r.get('exportValue', {}).get('value', 0)),
        'Total Imports': float(r.get('importValue', {}).get('value', 0))
    } for r in raw_data])

    #aggregate if multiple years exist
    df = df.groupby(['Partner', 'Partner ISO']).agg({
        'Total Exports': 'sum',
        'Total Imports': 'sum'
    }).reset_index()

    #calculate additional metrics
    df['Trade Balance'] = df['Total Exports'] - df['Total Imports']
    df['Total Trade'] = df['Total Exports'] + df['Total Imports']
    df['Export Share'] = (df['Total Exports'] / df['Total Exports'].sum()) * 100
    df['Import Share'] = (df['Total Imports'] / df['Total Imports'].sum()) * 100

    return df


#display trade partners metrics
def partners_display_metrics(df):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Trading Partners", len(df))

        #add total trade volume
        total_trade = df['Total Trade'].sum()
        st.metric("Total Trade Volume", format_number(total_trade))

    with col2:
        st.write("Top Export Markets")
        top_exporters = df.nlargest(3, 'Total Exports')
        for _, row in top_exporters.iterrows():
            st.write(f"{row['Partner']}: {format_number(row['Total Exports'])} ({row['Export Share']:.1f}%)")

    with col3:
        st.write("Top Import Sources")
        top_importers = df.nlargest(3, 'Total Imports')
        for _, row in top_importers.iterrows():
            st.write(f"{row['Partner']}: {format_number(row['Total Imports'])} ({row['Import Share']:.1f}%)")


#create treemap visualization
def partners_create_treemap(df, trade_type="exports"):
    if trade_type.lower() == "exports":
        values = 'Total Exports'
        title = 'Top Export Partners'
    else:
        values = 'Total Imports'
        title = 'Top Import Partners'

    #filter for top 15 partners
    plot_df = df.nlargest(15, values)

    fig = px.treemap(
        plot_df,
        path=['Partner'],
        values=values,
        title=title,
        color='Trade Balance',
        color_continuous_scale=['red', 'white', 'green'],
        color_continuous_midpoint=0
    )

    fig.update_layout(height=500)
    return fig


#add regional concentration analysis
def partners_create_regional_chart(df):
    region_mapping = {
        'Europe': ['ALB', 'AND', 'AUT', 'BLR', 'BEL', 'BIH', 'BGR', 'HRV', 'CZE', 'DNK',
                   'EST', 'FIN', 'FRA', 'DEU', 'GRC', 'HUN', 'ISL', 'IRL', 'ITA', 'LVA',
                   'LIE', 'LTU', 'LUX', 'MLT', 'MDA', 'MCO', 'MNE', 'NLD', 'MKD', 'NOR',
                   'POL', 'PRT', 'ROU', 'RUS', 'SMR', 'SRB', 'SVK', 'SVN', 'ESP', 'SWE',
                   'CHE', 'UKR', 'GBR', 'VAT'],

        'Asia': ['BGD', 'BTN', 'BRN', 'KHM', 'CHN', 'HKG', 'IND', 'IDN', 'JPN',
                 'LAO', 'MAC', 'MYS', 'MDV', 'MNG', 'MMR', 'NPL', 'PHL', 'SGP',
                 'KOR', 'LKA', 'TWN', 'THA', 'VNM'],

        'Middle East': ['ARM', 'AZE', 'BHR', 'CYP', 'GEO', 'IRN', 'IRQ', 'ISR',
                        'JOR', 'KWT', 'LBN', 'OMN', 'PAK', 'PSE', 'QAT', 'SAU',
                        'SYR', 'TUR', 'ARE', 'YEM', 'KAZ', 'KGZ', 'TJK', 'TKM',
                        'UZB'],

        'North America': ['CAN', 'MEX', 'USA'],

        'Central America & Caribbean': ['AIA', 'ATG', 'ABW', 'BHS', 'BRB', 'BLZ', 'BMU',
                                        'VGB', 'CYM', 'CRI', 'CUB', 'CUW', 'DMA', 'DOM',
                                        'SLV', 'GRD', 'GLP', 'GTM', 'HTI', 'HND', 'JAM',
                                        'MTQ', 'MSR', 'NIC', 'PAN', 'PRI', 'BES', 'KNA',
                                        'LCA', 'MAF', 'VCT', 'SXM', 'TTO', 'TCA', 'VIR'],

        'South America': ['ARG', 'BOL', 'BRA', 'CHL', 'COL', 'ECU', 'FLK', 'GUF', 'GUY',
                          'PRY', 'PER', 'SUR', 'URY', 'VEN'],

        'Africa': ['DZA', 'AGO', 'BEN', 'BWA', 'BFA', 'BDI', 'CPV', 'CMR', 'CAF', 'TCD',
                   'COM', 'COG', 'CIV', 'COD', 'DJI', 'EGY', 'GNQ', 'ERI', 'SWZ', 'ETH',
                   'GAB', 'GMB', 'GHA', 'GIN', 'GNB', 'KEN', 'LSO', 'LBR', 'LBY', 'MDG',
                   'MWI', 'MLI', 'MRT', 'MUS', 'MYT', 'MAR', 'MOZ', 'NAM', 'NER', 'NGA',
                   'REU', 'RWA', 'STP', 'SEN', 'SYC', 'SLE', 'SOM', 'ZAF', 'SSD', 'SDN',
                   'TZA', 'TGO', 'TUN', 'UGA', 'ESH', 'ZMB', 'ZWE'],

        'Oceania': ['AUS', 'COK', 'FJI', 'PYF', 'KIR', 'MHL', 'FSM', 'NRU', 'NCL', 'NZL',
                    'NIU', 'NFK', 'MNP', 'PLW', 'PNG', 'PCN', 'WSM', 'SLB', 'TKL', 'TON',
                    'TUV', 'UMI', 'VUT', 'WLF'],

        'Other': []  #default for unmapped countries
    }

    #add region column to DataFrame
    df['Region'] = df['Partner ISO'].map(lambda x: next(
        (region for region, countries in region_mapping.items() if x in countries), 'Other'))

    #create regional aggregation
    region_df = df.groupby('Region').agg({
        'Total Exports': 'sum',
        'Total Imports': 'sum'
    }).reset_index()

    fig = px.bar(
        region_df,
        x='Region',
        y=['Total Exports', 'Total Imports'],
        title='Trade by Region',
        barmode='group'
    )

    return fig


#main function to display trade partner tab
def partners_display_tab(sparql, iso_code, country_name):
    st.header("Trade Partners Analysis")

    #time period selector
    time_options = ["All Time", "Recent (Last 3 Years)", "Single Year"]
    selected_time = st.radio("Select Time Period", time_options, horizontal=True)

    #get available years and most recent year
    available_years, most_recent_year = get_available_years(sparql, iso_code)

    if not available_years:
        st.warning(f"No trade data available for {country_name}")
        return

    #convert selection to query parameter
    if selected_time == "Single Year":
        selected_year = st.selectbox(
            "Select Year",
            available_years,  #from def get_available_years
            key=f"year_select_partners_{iso_code}"  #unique key per country
        )
        time_period = selected_year
    else:
        time_period = "all" if selected_time == "All Time" else "recent"

    #get and process data
    raw_data = partners_get_data(sparql, iso_code, time_period)

    if not raw_data:
        st.warning(f"No trade partner data available for {country_name}")
        return

    #process data
    df = partners_process_data(raw_data)

    if df is None or len(df) == 0:
        st.warning(f"No trade data available for {country_name}")
        return

    #display metrics
    partners_display_metrics(df)

    #create visualization tabs
    viz_tab1, viz_tab2 = st.tabs(["Trade Partners Overview", "Regional Analysis"])

    with viz_tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(partners_create_treemap(df, "exports"), use_container_width=True)
        with col2:
            st.plotly_chart(partners_create_treemap(df, "imports"), use_container_width=True)

    with viz_tab2:
        st.plotly_chart(partners_create_regional_chart(df), use_container_width=True)


#key data for sociodemographic
def get_indicator_data(sparql, iso_code, measurement_type, value_property):
    query = f"""
    PREFIX : <http://example.org/country-data#>
    SELECT ?year ?value
    WHERE {{
        ?country a :Country ;
                :isoCode "{iso_code}" ;
                :{measurement_type} ?measurement .
        ?measurement :year ?year ;
                     :{value_property} ?value .
    }}
    ORDER BY ?year
    """

    results = execute_query(sparql, query)
    if results:
        return pd.DataFrame([
            {
                'Year': int(float(r['year']['value'])),
                'Value': float(r['value']['value'])
            } for r in results
        ])
    return pd.DataFrame()


#calculate change (YoY) for key numbers of sociodemographics
def calculate_change(current, previous):
    if previous == 0:
        return 0, True

    change = ((current - previous) / abs(previous)) * 100
    return change


#format change value (YoY) based on data type
def format_change(change, indicator_type):
    if indicator_type == 'Unemployment':
        #for unemployment, decrease is positive
        return f"{change:+.1f} pp", change < 0
    elif indicator_type in ['HDI', 'Democracy Index']:
        #for HDI and Democracy Index, increase is positive
        return f"{change:+.2f} points", change > 0
    else:
        #for population, show percentage
        return f"{change:+.2f}%", change > 0


#show sociodemographic data
def show_sociodemographic(sparql, iso_code, country_name):
    st.header("Sociodemographic Indicators")

    #create columns for key metrics
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    #population Data
    pop_df = get_indicator_data(sparql, iso_code, "hasDemographicMeasurement", "populationValue")
    if not pop_df.empty:
        latest_pop = pop_df.iloc[-1]
        if len(pop_df) >= 2:
            prev_pop = pop_df.iloc[-2]
            pop_change = calculate_change(latest_pop['Value'], prev_pop['Value'])
            pop_change_str, is_positive = format_change(pop_change, 'Population')
        else:
            pop_change_str = "No previous data"
            is_positive = None

        col1.metric(
            f"Population ({int(latest_pop['Year'])})",
            format_number(latest_pop['Value']),
            pop_change_str,
            delta_color="normal"
        )

    #HDI data
    hdi_df = get_indicator_data(sparql, iso_code, "hasSocialMeasurement", "hdiValue")
    if not hdi_df.empty:
        latest_hdi = hdi_df.iloc[-1]
        if len(hdi_df) >= 2:
            prev_hdi = hdi_df.iloc[-2]
            hdi_change = calculate_change(latest_hdi['Value'], prev_hdi['Value'])
            hdi_change_str, is_positive = format_change(hdi_change, 'HDI')
        else:
            hdi_change_str = "No previous data"
            is_positive = None

        col2.metric(
            f"Human Development Index ({int(latest_hdi['Year'])})",
            f"{latest_hdi['Value']:.3f}",
            hdi_change_str,
            delta_color="normal" if is_positive is None else ("normal" if is_positive else "inverse")
        )

    #unemployment data
    unemp_df = get_indicator_data(sparql, iso_code, "hasSocialMeasurement", "unemploymentValue")
    if not unemp_df.empty:
        latest_unemp = unemp_df.iloc[-1]
        if len(unemp_df) >= 2:
            prev_unemp = unemp_df.iloc[-2]
            unemp_change = latest_unemp['Value'] - prev_unemp['Value']  # Use absolute change for unemployment
            unemp_change_str, is_positive = format_change(unemp_change, 'Unemployment')
        else:
            unemp_change_str = "No previous data"
            is_positive = None

        col3.metric(
            f"Unemployment Rate ({int(latest_unemp['Year'])})",
            f"{latest_unemp['Value']:.1f}%",
            unemp_change_str,
            delta_color="normal" if is_positive is None else ("normal" if is_positive else "inverse")
        )

    #Democracy Index data
    dem_df = get_indicator_data(sparql, iso_code, "hasSocialMeasurement", "democracyIndexValue")
    if not dem_df.empty:
        latest_dem = dem_df.iloc[-1]
        if len(dem_df) >= 2:
            prev_dem = dem_df.iloc[-2]
            dem_change = calculate_change(latest_dem['Value'], prev_dem['Value'])
            dem_change_str, is_positive = format_change(dem_change, 'Democracy Index')
        else:
            dem_change_str = "No previous data"
            is_positive = None

        col4.metric(
            f"Democracy Index ({int(latest_dem['Year'])})",
            f"{latest_dem['Value']:.2f}",
            dem_change_str,
            delta_color="normal" if is_positive is None else ("normal" if is_positive else "inverse")
        )

    #create sub-tabs for visualizations only if data exists
    tabs = []
    if not pop_df.empty:
        tabs.append(("Population Trend", pop_df, "Population Count"))
    if not hdi_df.empty:
        tabs.append(("HDI Trend", hdi_df, "HDI Score"))
    if not unemp_df.empty:
        tabs.append(("Unemployment Trend", unemp_df, "Unemployment Rate (%)"))
    if not dem_df.empty:
        tabs.append(("Democracy Index Trend", dem_df, "Democracy Index Score"))

    if tabs:
        tab_list = st.tabs([tab[0] for tab in tabs])

        for i, (title, df, y_label) in enumerate(tabs):
            with tab_list[i]:
                fig = px.line(
                    df,
                    x='Year',
                    y='Value',
                    title=f'{title} - {country_name}'
                )
                fig.update_layout(
                    yaxis_title=y_label,
                    xaxis_title="Year",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"No sociodemographic data available for {country_name}")


def main():
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
        #create dynamic header with selected country
        st.header(f"🌍 Trade Data Analysis for {selected_country}")

        #main content area
        tab1, tab2, tab3 = st.tabs(["Trade Overview", "Trade Partners", "Sociodemographics"])

        with tab1:
            st.header("Trade Overview")
            if st.session_state.selected_iso and st.session_state.selected_country:
                show_trade_overview(sparql,
                                    st.session_state.selected_iso,
                                    st.session_state.selected_country)

        with tab2:
            partners_display_tab(sparql, selected_iso, selected_country)

        with tab3:
            show_sociodemographic(sparql, selected_iso, selected_country)

if __name__ == "__main__":
    main()
