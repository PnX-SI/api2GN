CHANGELOG
=========
1.0.0 (2026-11-23)
----------------------

Nécessite GeoNature 2.18 (ou plus)

**🚀 Nouveautés**

- Création d'un parseur permettant d'importer automatiquement les données depuis l'API du GBIF (#5 par @pierre56, @amandine-sahl, @lpofredc).

**🐛 Corrections**

- Ajout de la compatibilité avec SQLAlchemy 2.0.x (#8 par @amandine-sahl)
- Ajout de la vérification des permissions d'accès au module dans l'Admin de GeoNature (par @TheoLechemia)


1.0.0.rc1 (2023-08-11)
----------------------

Release candidate du module API2GN

**🤖 Fonctionnalité**

- Classe de haut niveau `JSONParser` et `WFSParser` permettant de parser respectivement des flux JSON et WFS
- Classe `GeoNatureParser` permettant de constuire des parsers connectant deux GeoNature entre eux
- Commande `geonature parser list` pour lister les parsers configurés
- Commande `geonature parser run <PARSER_NAME>` pour lancer une parser (option `dry-run` pour lancer sans insertion en base)
- Backoffice de gestion de tâches planifiées integré au backoffice de GeoNature


