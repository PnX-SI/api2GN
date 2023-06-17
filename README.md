# Installation

    #Depuis le venv de GeoNature
    source <GeoNature_DIR>/backend/venv/bin/activate
    pip install .

Copier le fichier d'exemple `var/config/parsers.example.py` en `var/config/parsers.py`

## Commandes 

* Lister les parsers disponibles

    ```    
    geonature parser list
    ```

- Lancer un parser
    ```
    geonature parser run <PARSER_NAME>
    ```


### TODO:

- Enlever "name" des parser. Le nom est celui de la classe (à remplacer par label ?)
