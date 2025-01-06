#define base and prefixes
@base <http://example.org/country-data#> .
@prefix : <http://example.org/country-data#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix time: <http://www.w3.org/2006/time#> .

#ontology declaration
<http://example.org/country-data> rdf:type owl:Ontology ;
    dc:title "Country Data Ontology"@en ;
    dc:description "An ontology for representing country data including economic and social indicators"@en ;
    dc:creator "Generated for Country Data Project"@en ;
    owl:versionInfo "1.0"@en ;
    dc:date "2024-12-12"^^xsd:date .

#base classes
:Entity rdf:type owl:Class ;
    rdfs:label "Entity"@en ;
    rdfs:comment "Base class for all entities in the ontology"@en .

:TemporalEntity rdf:type owl:Class ;
    rdfs:subClassOf :Entity ;
    rdfs:label "Temporal Entity"@en ;
    rdfs:comment "An entity with temporal characteristics"@en .

#main classes
:Country rdf:type owl:Class ;
    rdfs:subClassOf :Entity ;
    rdfs:label "Country"@en ;
    rdfs:comment "A sovereign state"@en ;
    owl:disjointWith :Organization .

:Organization rdf:type owl:Class ;
    rdfs:subClassOf :Entity ;
    rdfs:label "Organization"@en ;
    rdfs:comment "An international organization"@en .

:WorldAggregate rdf:type owl:Class ;
    rdfs:subClassOf :Entity ;
    rdfs:label "World Aggregate"@en ;
    rdfs:comment "Special entity representing global trade aggregates"@en .

:Measurement rdf:type owl:Class ;
    rdfs:subClassOf :TemporalEntity ;
    rdfs:label "Measurement"@en ;
    rdfs:comment "A measurement of an indicator at a specific time"@en .

:EconomicMeasurement rdf:type owl:Class ;
    rdfs:subClassOf :Measurement ;
    rdfs:label "Economic Measurement"@en ;
    rdfs:comment "Economic indicators like GDP"@en .

:SocialMeasurement rdf:type owl:Class ;
    rdfs:subClassOf :Measurement ;
    rdfs:label "Social Measurement"@en ;
    rdfs:comment "Social indicators like HDI"@en .

:DemographicMeasurement rdf:type owl:Class ;
    rdfs:subClassOf :Measurement ;
    rdfs:label "Demographic Measurement"@en ;
    rdfs:comment "Demographic indicators like Population"@en .

:TradeMeasurement rdf:type owl:Class ;
    rdfs:subClassOf :Measurement ;
    rdfs:label "Trade Measurement"@en ;
    rdfs:comment "Measurement of trade flows between countries"@en .

:TradeAggregate rdf:type owl:Class ;
    rdfs:subClassOf :TradeMeasurement ;
    rdfs:label "Trade Aggregate"@en ;
    rdfs:comment "Aggregated trade measurements including totals and balances"@en .

:GoodsTrade rdf:type owl:Class ;
    rdfs:subClassOf :TradeMeasurement ;
    rdfs:label "Goods Trade"@en ;
    rdfs:comment "Measurement of trade in physical goods (type code C)"@en .

:ServicesTrade rdf:type owl:Class ;
    rdfs:subClassOf :TradeMeasurement ;
    rdfs:label "Services Trade"@en ;
    rdfs:comment "Measurement of trade in services (type code S)"@en .

#object properties
:hasMeasurement rdf:type owl:ObjectProperty ;
    rdfs:domain :Country ;
    rdfs:range :Measurement ;
    rdfs:label "has measurement"@en .

:hasEconomicMeasurement rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasMeasurement ;
    rdfs:domain :Country ;
    rdfs:range :EconomicMeasurement ;
    rdfs:label "has economic measurement"@en .

:hasSocialMeasurement rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasMeasurement ;
    rdfs:domain :Country ;
    rdfs:range :SocialMeasurement ;
    rdfs:label "has social measurement"@en .

:hasDemographicMeasurement rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasMeasurement ;
    rdfs:domain :Country ;
    rdfs:range :DemographicMeasurement ;
    rdfs:label "has demographic measurement"@en .

:hasTradeMeasurement rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasMeasurement ;
    rdfs:domain :Country ;
    rdfs:range :TradeMeasurement ;
    rdfs:label "has trade measurement"@en .

:hasTradeAggregate rdf:type owl:ObjectProperty ;
    rdfs:subPropertyOf :hasTradeMeasurement ;
    rdfs:domain :Country ;
    rdfs:range :TradeAggregate ;
    rdfs:label "has trade aggregate"@en .

:hasPartnerCountry rdf:type owl:ObjectProperty ;
    rdfs:domain :TradeMeasurement ;
    rdfs:range :Country ;
    rdfs:label "has partner country"@en ;
    rdfs:comment "Links trade measurement to partner country"@en .

:isMemberOf rdf:type owl:ObjectProperty ;
    rdfs:domain :Country ;
    rdfs:range :Organization ;
    rdfs:label "is member of"@en .

:hasNeighbor rdf:type owl:ObjectProperty ;
    rdfs:domain :Country ;
    rdfs:range :Country ;
    rdfs:label "has neighbor"@en ;
    rdf:type owl:SymmetricProperty .

#data properties
:isoCode rdf:type owl:DatatypeProperty ;
    rdfs:domain :Country ;
    rdfs:range xsd:string ;
    rdfs:label "ISO Alpha-3 code"@en ;
    rdf:type owl:FunctionalProperty .

:unCode rdf:type owl:DatatypeProperty ;
    rdfs:domain :Country ;
    rdfs:range xsd:string ;
    rdfs:label "UN Country Code"@en ;
    rdfs:comment "1-3 digit code used by the UN to identify countries"@en .

:name rdf:type owl:DatatypeProperty ;
    rdfs:domain :Entity ;
    rdfs:range xsd:string ;
    rdfs:label "name"@en .

:gdpValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :EconomicMeasurement ;
    rdfs:range xsd:decimal ;
    rdfs:label "GDP value"@en .

:hdiValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :SocialMeasurement ;
    rdfs:range xsd:decimal ;
    rdfs:label "HDI value"@en .

:democracyIndexValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :SocialMeasurement ;
    rdfs:range xsd:decimal ;
    rdfs:label "Democracy Index value"@en .

:populationValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :DemographicMeasurement ;
    rdfs:range xsd:integer ;
    rdfs:label "Population value"@en .

:tradeValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeMeasurement ;
    rdfs:range xsd:decimal ;
    rdfs:label "Trade Value"@en ;
    rdfs:comment "Value of trade in US Dollars"@en .

# Trade aggregate properties
:totalExportValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeAggregate ;
    rdfs:range xsd:decimal ;
    rdfs:label "Total Export Value"@en ;
    rdfs:comment "Total value of exports (goods + services)"@en .

:totalImportValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeAggregate ;
    rdfs:range xsd:decimal ;
    rdfs:label "Total Import Value"@en ;
    rdfs:comment "Total value of imports (goods + services)"@en .

:goodsExportValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeAggregate ;
    rdfs:range xsd:decimal ;
    rdfs:label "Goods Export Value"@en .

:goodsImportValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeAggregate ;
    rdfs:range xsd:decimal ;
    rdfs:label "Goods Import Value"@en .

:servicesExportValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeAggregate ;
    rdfs:range xsd:decimal ;
    rdfs:label "Services Export Value"@en .

:servicesImportValue rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeAggregate ;
    rdfs:range xsd:decimal ;
    rdfs:label "Services Import Value"@en .

:totalTradeBalance rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeAggregate ;
    rdfs:range xsd:decimal ;
    rdfs:label "Total Trade Balance"@en ;
    rdfs:comment "Total exports minus total imports"@en .

:goodsTradeBalance rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeAggregate ;
    rdfs:range xsd:decimal ;
    rdfs:label "Goods Trade Balance"@en .

:servicesTradeBalance rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeAggregate ;
    rdfs:range xsd:decimal ;
    rdfs:label "Services Trade Balance"@en .

:flowType rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeMeasurement ;
    rdfs:range xsd:string ;
    rdfs:label "Flow Type"@en ;
    rdfs:comment "Type of trade flow (Import or Export)"@en .

:tradeType rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeMeasurement ;
    rdfs:range xsd:string ;
    rdfs:label "Trade Type"@en ;
    rdfs:comment "Type of trade (C for Goods, S for Services)"@en .

:year rdf:type owl:DatatypeProperty ;
    rdfs:domain :TemporalEntity ;
    rdfs:range xsd:integer ;
    rdfs:label "Year of measurement"@en .

:timestamp rdf:type owl:DatatypeProperty ;
    rdfs:domain :TemporalEntity ;
    rdfs:range xsd:dateTime ;
    rdfs:label "Exact timestamp of measurement"@en .

# Growth rate properties for year-over-year comparison
:growthRate rdf:type owl:DatatypeProperty ;
    rdfs:domain :TradeAggregate ;
    rdfs:range xsd:decimal ;
    rdfs:label "Growth Rate"@en ;
    rdfs:comment "Year-over-year growth rate in percentage"@en .

#annotations for measurements
:measurementUnit rdf:type owl:AnnotationProperty ;
    rdfs:label "Measurement Unit"@en .

:gdpValue rdfs:comment "GDP in current US dollars"@en ;
    :measurementUnit "USD" .

:hdiValue rdfs:comment "Human Development Index on a scale of 0 to 1"@en ;
    :measurementUnit "Index" .

:democracyIndexValue rdfs:comment "Democracy Index on a scale of 0 to 10"@en ;
    :measurementUnit "Index" .

:populationValue rdfs:comment "Total population count"@en ;
    :measurementUnit "People" .

:tradeValue rdfs:comment "Trade value in current US dollars"@en ;
    :measurementUnit "USD" .

# Trade balance annotations
:totalTradeBalance rdfs:comment "Total trade balance in US dollars"@en ;
    :measurementUnit "USD" .

:goodsTradeBalance rdfs:comment "Goods trade balance in US dollars"@en ;
    :measurementUnit "USD" .

:servicesTradeBalance rdfs:comment "Services trade balance in US dollars"@en ;
    :measurementUnit "USD" .

# Individual declaration for World
:W00 rdf:type :WorldAggregate ;
    :name "World"@en ;
    :unCode "0" ;
    :isoCode "W00" .