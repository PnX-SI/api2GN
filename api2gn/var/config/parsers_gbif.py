from api2gn.parsers import WFSParser
from api2gn.geonature_parser import GeoNatureParser
from api2gn.gbif_parser import GBIFParser

# Fichier a renommer en parsers.py pour fonctionner car parsers.py dans .gitignore
# Amélioration a faire, un fichier par parser

### Exemple func
# def my_custom_func(value):
#     """
#     Custom function to fill "observers" synthese with a depending api value
#     """
#     if value == "Org 1":
#         return "Observateur inconnu"
#     else:
#         return "Observateur 1"


class GBIFParserInaturalist(GBIFParser):
    name = "GBIF_INaturalist"
    description = "Le Parser GBIF_INaturalist permet de récupérer les données en provenance de INaturalist depuis la plateforme du GBIF. Vous pouvez mettre un JDD et une zone geographique, ou une liste d'identifiants" 
    # url = "" # pas nécessaire car usage de la lib pygbif

    limit = 100 # Limit du parser, mettre équivalent du limit de l'API
    # filter api search occurences
    # Mettre en commentaire pour utiliser la recherche par id_occurence
    ## Vous pouvez remplacer les valeurs pour filtrer
    api_filters = {
        "datasetKey": "50c9509d-22c7-4a22-a47d-8c48425ef4a7", ## INaturalist research grade
        "wkt" : "POLYGON((-5.3685 46.16181,-0.53236 46.16181,-0.53236 49.21621,-5.3685 49.21621,-5.3685 46.16181))", ## Polygon Bretagne -> get via url de https://www.gbif.org/occurrence/map?
        "limit" : "100" , 
        }
    
    # Mettre en commentaire pour utiliser la recherche API
    ## Vous pouvez remplacer par une liste dynamique d'IDs
    # occurrence_ids = [4508012001]
    # occurrence_ids = [4508012001, 4507897058, 4507948047, 4507718106, 4507942081]
    
    #--> La recherche par id est prioritaire sur la recherche par filtre

    ### Exemple dynamic_fields 
    # dynamic_fields = {
    #     # "unique_dataset_id" : "69f26484-08b6-4ccf-aeeb-42124d124fa1", # JDD test Inaturalist
    #     # "id_dataset" : 705
    # #    # "occurence_id" : "4407389321",
    # #     "altitude_min": my_custom_func
    # }

    # override existant GeoNatureParser mapping
    # the key is the name of the column is synthese
    # the value could be a str of the column in the API or a dict for a custom value

    mapping = {
        # "unique_id_sinp": "xxx",
        # "unique_id_sinp_grp": "xxx",
        "date_min": "eventDate",
        "date_max": "eventDate",
        "nom_cite": "scientificName",
        "observers": "recordedBy",
        "determiner": "recordedBy",
        "meta_create_date": "eventDate",
        "meta_update_date": "eventDate",
        "place_name": "verbatimLocality",
    }

    # pass constant from missing value in my API
    constant_fields = {
        "id_source": 16, # a creer ou a récupérer depuis metadonnées
        "id_dataset": 705, # Creer JDD test, a terme récupérer les métadonnées et creer JDD en auto
        "count_min": 1, # Non disponible dans api
        "count_max": 1, # Non disponible dans api
        # "cd_nom":  4001,

    }
