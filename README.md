# Trade Data Analyzer
This project allows for the analysis of trade data as reported by the United Nations and available through [UN Comtrade](https://comtradeplus.un.org/). Additional data was added using the [SPARQL endpoint of Wikidata](https://query.wikidata.org/). After aggregation of the data, you can then explore using a locally hosted Streamlit dashboard.
<br/>
<br/>

> [!Note]
> After downloading this repository _as is_, a version of the project can be run immediately. However, there is no direct connection to UN Comtrade, as this would violate their [use and re-dissemination policy](https://uncomtrade.org/docs/policy-on-use-and-re-dissemination/#fairusage).
<br/>
<br/>


## Requirements
- Python 3.12
- packages within [requirements.txt](requirements.txt)
- locally deployed Apache Jena Fuseki server ([app.py](dashboard/app.py) is querying towards `localhost:3030`)
- UN Comtrade data
<br/>
<br/>

## Content
This project contains python scripts, a .csv file with some example data from UN comtrade and an empty .ttl file. They are structured within this repository as follows:

- dashboard
  - app.py <sub>_#streamlit dashboard_</sub>
- data
  - country_ontology.py <sub>_#ontology for RDF graph_</sub>
  - countrydata.ttl <sub>_#empty turtle file to store data from main.py_</sub>
  - main.py <sub>_#script to aggregate data from wikidata and .csv to countrydata.ttl_</sub>
  - plasticstraw.py <sub>_#script to purge countrydata.ttl_</sub>
  - sircalcalot.py <sub>_#script to enhance countrydata.ttl with trade balance calculations_</sub>
  - uncomtrade.csv <sub>_#data downloaded from UN comtrade for the years 2014-2023_</sub>
  - wikidata_queries.py <sub>_#SPARQL queries for wikidata_</sub>
<br/>
<br/>

## Instructions
To be able to start the dashboard you need to execute the following steps:
1. get the UN Comtrade data and save it into .csv **OR** use data from this repo
2. `run` [main.py](data/main.py)
3. `run` [sircalcalot.py](data/sircalcalot.py)
4. install[^1] and run[^2] local Fuseki server
5. upload countrydata_calculated.ttl[^3] to Fuseki as countrydata_calculated[^4]
6. `run` [app.py](dashboard/app.py)
<br/>
Streamlit then deploys the dashboard to http://localhost:8501/ and is ready for exploration.
<br/>

[^1]: check [Apache Jena Fuseki Download here](https://jena.apache.org/download/index.cgi) or download using [`homebrew`](https://formulae.brew.sh/formula/fuseki).
[^2]: check [Fuseki Quickstart](https://jena.apache.org/documentation/fuseki2/fuseki-quick-start.html) or use homebrew via terminal command (macOS) `/opt/homebrew/opt/fuseki/bin/fuseki-server`
[^3]: will be generated when executing [sircalcalot.py](data/sircalcalot.py)
[^4]: [app.py](dashboard/app.py) is querying `http://localhost:3030/countrydata_calculated/query`