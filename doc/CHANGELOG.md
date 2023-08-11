CHANGELOG
=========

1.0.0.rc1 (2023-08-11)
----------------------

Release candidate du module API2GN

**🤖 Fonctionnalité**

- Classe de haut niveau `JSONParser` et `WFSParser` permettant de parser respectivement des flux JSON et WFS
- Classe `GeoNatureParser` permettant de constuire des parsers connectant deux GeoNature entre eux
- Commande `geonature parser list` pour lister les parsers configurés
- Commande `geonature parser run <PARSER_NAME>` pour lancer une parser (option `dry-run` pour lancer sans insertion en base)
- Backoffice de gestion de tâches planifiées integré au backoffice de GeoNature


