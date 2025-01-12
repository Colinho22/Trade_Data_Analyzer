class WikidataQueries:

#function to filter for a specific year --> if no year is added the queries will pull all available data
    def __init__(self, year=None):
        self.year = year
        self._year_filter = f"FILTER(?year = {YEAR})" if year else ""

#get all countries and isoAlpha3 codes to link additional data together
    @staticmethod
    def get_base_country_query():
        return """
        SELECT DISTINCT ?country ?countryLabel ?isoCode
        WHERE {
            { ?country wdt:P31 wd:Q6256. } # Sovereign states
            UNION
            { ?country wdt:P31/wdt:P279* wd:Q3624078. } # Independent political entities
            ?country wdt:P298 ?isoCode. # Must have ISO Alpha-3 code
            SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }
        ORDER BY ?countryLabel
        """

#get gdp data for one/all years available
    def get_gdp_query(self):
        return f"""
        SELECT DISTINCT ?country ?isoCode ?gdp ?year
        WHERE {{
            ?country wdt:P31 wd:Q6256.
            ?country wdt:P298 ?isoCode.
            ?country p:P2131 ?gdpStatement.
            ?gdpStatement ps:P2131 ?gdp;
                        pq:P585 ?gdpDate.
            BIND(YEAR(?gdpDate) as ?year)
            {self._year_filter}
        }}
        ORDER BY ?isoCode ?year
        """

#get human development index (hdi) data for one/all years available
    def get_hdi_query(self):
        return f"""
        SELECT DISTINCT ?country ?isoCode ?hdi ?year
        WHERE {{
            ?country wdt:P31 wd:Q6256.
            ?country wdt:P298 ?isoCode.
            ?country p:P1081 ?hdiStatement.
            ?hdiStatement ps:P1081 ?hdi;
                        pq:P585 ?hdiDate.
            BIND(YEAR(?hdiDate) as ?year)
            {self._year_filter}
        }}
        ORDER BY ?isoCode ?year
        """

#get democracy index data for one/all years available
    def get_democracy_index_query(self):
        return f"""
        SELECT DISTINCT ?country ?isoCode ?democracyIndex ?year
        WHERE {{
            ?country wdt:P31 wd:Q6256.
            ?country wdt:P298 ?isoCode.
            ?country p:P8328 ?demoStatement.
            ?demoStatement ps:P8328 ?democracyIndex;
                         pq:P585 ?demoDate.
            BIND(YEAR(?demoDate) as ?year)
            {self._year_filter}
        }}
        ORDER BY ?isoCode ?year
        """

#get population data for one/all years available
    def get_population_query(self):
        return f"""
        SELECT DISTINCT ?country ?isoCode ?population ?year
        WHERE {{
            ?country wdt:P31 wd:Q6256.
            ?country wdt:P298 ?isoCode.
            ?country p:P1082 ?popStatement.
            ?popStatement ps:P1082 ?population;
                        pq:P585 ?popDate.
            BIND(YEAR(?popDate) as ?year)
            {self._year_filter}
        }}
        ORDER BY ?isoCode ?year
        """

#get country's memberships in international organisations (i.e. defense or trade alliances)
    @staticmethod
    def get_membership_query():
        return """
        SELECT DISTINCT ?country ?isoCode ?org ?orgLabel
        WHERE {
            ?country wdt:P31 wd:Q6256.
            ?country wdt:P298 ?isoCode.
            ?country wdt:P463 ?org.
            SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }
        ORDER BY ?isoCode
        """

#get unemployment data for one/all years available
    def get_unemployment_query(self):
        return f"""
        SELECT DISTINCT ?country ?isoCode ?unemploymentRate ?year
        WHERE {{
            ?country wdt:P31 wd:Q6256.
            ?country wdt:P298 ?isoCode.
            ?country p:P1198 ?unemploymentStatement.
            ?unemploymentStatement ps:P1198 ?unemploymentRate;
                         pq:P585 ?unemploymentDate.
            BIND(YEAR(?unemploymentDate) as ?year)
            {self._year_filter}
        }}
        ORDER BY ?isoCode ?year
        """