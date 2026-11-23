from api2gn.parsers import WFSParser
from api2gn.geonature_parser import GeoNatureParser
from api2gn.gbif_parser import GBIFParser

# Fichier a renommer en parsers.py pour fonctionner car parsers.py dans .gitignore
# Amélioration a faire, un fichier par parser


class GBIFParserInaturalist(GBIFParser):
    name = "GBIF_INaturalist"
    description = "Le Parser GBIF_INaturalist permet de récupérer les données en provenance de INaturalist depuis la plateforme du GBIF."
    # url = "" # pas nécessaire car usage de la lib pygbif

    limit = 300  # Limit du parser, mettre équivalent du limit de l'API
    # filter api search occurences
    # Mettre en commentaire pour utiliser la recherche par id_occurence
    ## Vous pouvez remplacer les valeurs pour filtrer
    #   Documentation complète: https://techdocs.gbif.org/en/openapi/v1/occurrence#/Searching%20occurrences/searchOccurrence
    api_filters = {
        "datasetKey": "50c9509d-22c7-4a22-a47d-8c48425ef4a7",  ## INaturalist research grade
        "geometry": "POLYGON ((3.221396682915761 43.97662194206563, 3.221396682915761 44.515887254953945, 3.9549009899856746 44.515887254953945, 3.9549009899856746 43.97662194206563, 3.221396682915761 43.97662194206563))",
        "limit": limit,
    }

    # Création des dataset
    create_dataset = True

    # pass constant from missing value in my API
    constant_fields = {
        "id_source": -1,  # a créer ou a récupérer depuis metadonnées
    }


class GBIFParserOrgAllDatasets(GBIFParser):
    name = "GBIF_INaturalist_org"
    description = (
        "Le Parser GBIFParserOrgAllDatasets permet de récupérer les données en provenance du GBIF."
    )

    limit = 300  # Limit du parser, mettre équivalent du limit de l'API
    # filter api search occurences
    # Mettre en commentaire pour utiliser la recherche par id_occurence
    ## Vous pouvez remplacer les valeurs pour filtrer
    api_filters = {
        "publishing_org": [
            "e2e717bf-551a-4917-bdc9-4fa0f342c530",  # Cornell lab
            "c8d737e0-2ff8-42e8-b8fc-6b805d26fc5f",  # observations.org
            "28eb1a3f-1c15-4a95-931a-4af90ecb574d",  # iNaturalist
            "64ee55c9-570a-42af-b7da-3f13c6b4e5a9",  # Swiss National Biodiversity Data and Information Cen...
            "76c3443b-bf10-4fb6-a6e7-aeaa65be383c",  # ENGIE
            "d3f94e8a-bb06-4d2b-89a6-6cd66abfa66c",  # EBCC
            "bb646dff-a905-4403-a49b-6d378c2cf0d9",  # naturgucker.de
            "1f00d75c-f6fc-4224-a595-975e82d7689c",  # Xeno-canto Foundation for Nature Sounds
            "9661d20d-86b6-4485-8948-f3c86b022fa7",  # SwissNatColl
        ],
        "geometry": "POLYGON ((3.221396682915761 43.97662194206563, 3.221396682915761 44.515887254953945, 3.9549009899856746 44.515887254953945, 3.9549009899856746 43.97662194206563, 3.221396682915761 43.97662194206563))",
        "limit": limit,
    }
    force_import = True
    create_dataset = True
    # pass constant from missing value in my API
    constant_fields = {
        "id_source": -1,  # a creer ou a récupérer depuis metadonnées
    }
