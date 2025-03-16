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


#get enhanced data about organizations including their types
    @staticmethod
    def get_enhanced_membership_query():
        """Get enhanced data about organizations including their types"""
        return """
            SELECT DISTINCT ?country ?isoCode ?org ?orgLabel ?orgDescription ?orgType ?orgTypeLabel
            WHERE {
                # Get country and its organization memberships
                ?country wdt:P31 wd:Q6256.
                ?country wdt:P298 ?isoCode.
                ?country wdt:P463 ?org.
    
                # Get organization types (P31 = instance of)
                OPTIONAL {
                    ?org wdt:P31 ?orgType.
    
                    # Filter for common organization classifications
                    FILTER(?orgType IN (
                        wd:Q43229,    # international organization
                        wd:Q10861173, # intergovernmental organization
                        wd:Q1331793,  # economic union
                        wd:Q1070167,  # supranational organization
                        wd:Q48349,    # economic community
                        wd:Q15911314, # economic organization
                        wd:Q865895,   # military alliance
                        wd:Q45400917, # trade bloc
                        wd:Q83267,    # united nations specialized agency
                        wd:Q19633155, # regional economic community
                        wd:Q1288568   # customs union
                    ))
                }
    
                # Get optional description
                OPTIONAL {
                    ?org schema:description ?orgDescription.
                    FILTER(LANG(?orgDescription) = "en")
                }
    
                # Get labels for all entities
                SERVICE wikibase:label { 
                    bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". 
                    ?org rdfs:label ?orgLabel.
                    ?orgType rdfs:label ?orgTypeLabel.
                }
            }
            ORDER BY ?isoCode ?orgLabel
            """


    @staticmethod
    def get_organization_details_query():
        """Get detailed information about specific organizations"""
        return """
            SELECT DISTINCT ?org ?orgLabel ?orgDescription ?website ?inception ?headquarters ?headquarters_label ?memberCount
            WHERE {
                # Identify international organizations
                ?org wdt:P31/wdt:P279* wd:Q43229.  # instance of/subclass of international organization
    
                # Get optional properties
                OPTIONAL { ?org wdt:P856 ?website. }           # website
                OPTIONAL { ?org wdt:P571 ?inception. }         # date of inception
                OPTIONAL { ?org wdt:P159 ?headquarters.        # headquarters location
                          ?headquarters rdfs:label ?headquarters_label.
                          FILTER(LANG(?headquarters_label) = "en") }
    
                # Get description
                OPTIONAL {
                    ?org schema:description ?orgDescription.
                    FILTER(LANG(?orgDescription) = "en")
                }
    
                # Count number of members (P463 = member of, so we need the inverse)
                {
                    SELECT ?org (COUNT(?member) as ?memberCount)
                    WHERE {
                        ?member wdt:P463 ?org.
                    }
                    GROUP BY ?org
                }
    
                # Get labels
                SERVICE wikibase:label { 
                    bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". 
                }
            }
            LIMIT 500  # Limit to avoid timeout
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