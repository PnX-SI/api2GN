from pygbif import occurrences, registry, species
from geojson import Feature
from shapely import wkt
from sqlalchemy.sql import func
from geoalchemy2.shape import from_shape
from api2gn.parsers import JSONParser
import json  
import requests


def fetch_taxref_cd_nom(self):
    try:
        # print('fetch_taxref_cd_nom self')
        response = occurrences.get(self['key'])
        # print(response['taxonKey'])
        # print('fetch_taxref_cd_nom self key')
        url = "https://taxref.mnhn.fr/api/taxa/findByExternalId?externalDbId=gbif&externalId=" + str(response['taxonKey'])
        
        response = requests.get(url)
        response.raise_for_status()
        response = response.json()
        # print('fetch_taxref_cd_nom')
        # print(response['referenceId'])
        
        if len(str(response['referenceId'])) == 0:
            return '183716  ' ## animalia
        else:
            return str(response['referenceId'])
    except Exception as e:
        # Handle the error and return a default value or an error code
        print(f"An error occurred: {e}")
        response = occurrences.get(self['key'])
        url = "https://taxref.mnhn.fr/api/taxa/fuzzyMatch?term=" + str(response['scientificName'])
        print(response)

        response = requests.get(url)
        response.raise_for_status()
        response = response.json()
        
        # Access the referenceId in the JSON response
        reference_id = response['_embedded']['taxa'][0]['referenceId']
        
        # Return the referenceId as a string
        return str(reference_id)


class GBIFParser(JSONParser):
    srid = 4326
    progress_bar = False  # useless multiple single request
    occurrence_ids = []  # Occurence par défaut 

    def __init__(self):
        print(self.occurrence_ids)
        self.api_filters = {**GBIFParser.api_filters, **self.api_filters}
        self.mapping = {**GBIFParser.mapping, **self.mapping}
        self.constant_fields = {
            **GBIFParser.constant_fields,
            **self.constant_fields,
        }
        # Initialize the parent class
        super().__init__()

        self.occurrence_id = None  # Initialisation
        self.data = None
        self.organization_data = None
        self.dataset_data = None
        self.species_data = None
        self.subdivisions_data = None
        self.cd_nom = None

        self.validate_maping()

        if len(self.occurrence_ids) < 1 :
            self.occurrence_ids = self.fetch_occurrence_ids_search()
            print("Liste des IDs d'occurrence :", self.occurrence_ids)

        
    def fetch_occurrence_ids_search(self):
        occurrence_ids = []
        print(self.api_filters )
        response = occurrences.search(datasetKey=self.api_filters['datasetKey'],geometry=self.api_filters['wkt'], limit=self.api_filters['limit'])
        print('data fetch_occurrence_ids_search')
        print(response)
        if 'results' in response and len(response['results']) > 0:
            for result in response['results']:
            # Accéder directement à la clé du deuxième niveau
                if 'key' in result:
                    occurrence_ids.append(result['key'])
                    print(occurrence_ids)
            return occurrence_ids
        elif 'data' in response:
            return response['data']
        elif len(response) > 0:
            for result in response: 
                if 'key' in result:
                    occurrence_ids.append(result['key'])
                    # print(occurrence_ids)
                return occurrence_ids
        else:
            raise ValueError(f"Failed to fetch data for search ")

    def fetch_occurrence_data(self, occurrence_id):
        response = occurrences.get(occurrence_id)
        print(response)  # Imprime la réponse complète pour inspecter la structure
        if 'results' in response and len(response['results']) > 0:
            return response['results'][0]
        elif 'data' in response:
            return response['data']
        elif len(response) > 0:
            return response
        else:
            raise ValueError(f"Failed to fetch data for occurrence ID {occurrence_id}")

    def fetch_organization_data(self):
        organization_key = self.data.get('publishingOrgKey')
        print(organization_key)
        if organization_key:
            return registry.organizations(uuid=organization_key)
        return {}

    def fetch_dataset_data(self):
        dataset_key = self.data.get('datasetKey')
        if dataset_key:
            return registry.datasets(uuid=dataset_key)
        return {}

    def fetch_species_data(self):
        taxon_key = self.data.get('taxonKey')
        print('fetch_species_data')
        print(taxon_key)
        if taxon_key:
            return species.name_usage(key=taxon_key)
        return {}
    

    def fetch_subdivisions_data(self):
        url = "https://api.gbif.org/v1/geocode/gadm/FRA.3_1/subdivisions"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    @property
    def items(self):
        return [self.data]  # Return data as a list with a single item

    @property
    def total(self):
        return len(self.occurrence_ids)  # Nombre total d'occurrences

    @property
    def total(self):
        return len(self.occurrence_ids)  # Nombre total d'occurrences

    def get_geom(self, row):
        if 'decimalLatitude' in row and 'decimalLongitude' in row:
            point = f"POINT({row['decimalLongitude']} {row['decimalLatitude']})"
            geom = wkt.loads(point)
            return from_shape(geom, srid=4326)
        return None

    def integrate_data(self):
        integrated_data = self.data.copy()
        integrated_data['organization'] = self.organization_data
        integrated_data['dataset'] = self.dataset_data
        integrated_data['species'] = self.species_data
        integrated_data['cd_nom'] = self.cd_nom
        # integrated_data['subdivisions'] = self.subdivisions_data
        return integrated_data

    def next_row(self):
        for occurrence_id in self.occurrence_ids:
            self.occurrence_id = occurrence_id
            self.data = self.fetch_occurrence_data(occurrence_id)
            self.organization_data = self.fetch_organization_data()
            self.dataset_data = self.fetch_dataset_data()
            self.species_data = self.fetch_species_data()
            self.subdivisions_data = self.fetch_subdivisions_data()
            yield self.data

    # Surcouchage pour test
    # def run(self, dry_run):
    #     if dry_run:
    #         print("Running in dry run mode")
    #         integrated_data = self.integrate_data()

    #         print(integrated_data)
    #         print(self.total)
    #         for item in self.items:
    #             print(self.get_geom(item))
    #     else:
    #         print("Running in normal mode")

### Mapping a améliorer
    mapping = {
        # "unique_id_sinp" : "identifier",
        "date_min": "eventDate",
        "date_max": "eventDate",
        "nom_cite": "scientificName",
        "count_min": 1,
        "count_max": 1,
        "observers": "recordedBy",
        "determiner": "recordedBy",
        "meta_create_date": "eventDate",
        "meta_update_date": "eventDate",
        "place_name": "verbatimLocality",
        "entity_source_pk_value": "catalogNumber",
    }
    dynamic_fields = {
        # "unique_dataset_id" : "69f26484-08b6-4ccf-aeeb-42124d124fa1", # JDD test Inaturalist
        # "id_dataset" : 705
        # "occurence_id" : "4407389321",
        # "altitude_min": my_custom_func
        
        "cd_nom": fetch_taxref_cd_nom        
    }

