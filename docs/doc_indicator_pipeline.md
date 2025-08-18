# Documentation indicator-pipeline

# 🧭 Vue d’ensemble

- L’objectif de ce pipeline est de calculer des indicateurs à partir du signal SpO₂ des fichiers de polysomnographie (*.edf* et annotations en *.csv*, *.txt* et/ou *.rtf*) disponibles sur le serveur de stockage. Les fichiers de polysomnographie sont d’abord convertis au format *sleeplab* (*slf*), et stockés à la fois sur le serveur de stockage et en local. Puis le calcul des indicateurs par le logiciel se fait manuellement via [ABOSA](https://zenodo.org/records/6962129), et enfin les données en sortie du logiciel sont intégrées dans la base de données MARS.
- Ce pipeline a été créé pour une utilisation sur une machine dédiée ou une VM sous Windows.
- Les données d’entrée sont les données de polysomnographie présentes sur le serveur de stockage. En sortie, on retrouve les indicateurs calculés dans les tables MARS dédiées aux mesures d’oxymétrie.

## 📄 Description du flux d’exécution

- **Connexion au serveur SFTP** : récupération des fichiers .*edf* et fichiers d’annotations (.*csv*, .*txt*, .*rtf*) pour les années spécifiées.
- **Conversion sleeplab** : transformation des fichiers de polysomnographie au format sleeplab (via le module `sleeplab_converter`). Les fichiers convertis sont enregistrés:
    - sur le **serveur de stockage**, dans le dossier du patient correspondant, sous le nom `slf_PAxxxx_Vx`;
    - en **local**, dans le dossier `slf-output`, situé un niveau au-dessus de la racine du projet
- **Lancement manuel d’ABOSA** *(hors pipeline)* : les fichiers convertis doivent être ouverts et analysés **manuellement** dans le logiciel ABOSA afin d’y calculer les indicateurs d’oxymétrie. Le logiciel génère en sortie plusieurs dossiers, chacun contenant un ou plusieurs fichiers Excel. Ces fichiers regroupent les indicateurs extraits, ainsi que des métadonnées sur les enregistrements analysés.
- **Import dans MARS** : les résultats générés par ABOSA sont sous forme de fichiers Excel. Les indicateurs conservés sont dans le fichier *ParameterValues*. Ils sont intégrés dans les tables appropriées de la base de données MARS, à partir d’une méthode POST qui envoie ces données à une API sous forme de payloads *json*.

---

# 🔧 Stack technique

- **Langage principal** : Python 3.10+
- **Structure du projet** : Organisation modulaire sous `src/` avec deux packages :
    - `indicator_pipeline` : gestion des connexions, conversions, interactions DB
    - `sleeplab_converter` : conversion des données PSG au format sleeplab
- **Orchestration du pipeline** : `Snakemake` (défini dans le `Snakefile`)
- **Environnement reproductible** via `Docker` (défini dans le `Dockerfile`) pour garantir la reproductibilité de l’environnement d’exécution
- **Gestion de projet & dépendances** : `pyproject.toml`
- **Logs** : Configuration personnalisée avec `logging_config.py`
- **Connexion SFTP** : Utilisation d’un client SFTP maison (`sftp_client.py`)
- **Base de données** : Intégration dans la base MARS (MySQL)
- **Formats manipulés** :
    - Fichiers **EDF** (biosignaux)
    - Fichiers d’**annotations** (*.csv*, *.txt*, *.rtf*)
    - Fichiers **Excel**
- **Librairies externes** :
    - Manipulation des fichiers EDF : `pyedflib`, `mne`
    - Traitement des données : `pandas`, `numpy`, `tqdm`, `openpyxl`
    - Connexions & système : `paramiko`, `python-dotenv`
    - Fichiers spécifiques : `striprtf`, `sleeplab-format`
- **Environnement cible** : Machine dédiée ou VM sous Windows (le système est requis pour exécuter ABOSA, incompatible avec Linux ou macOS)

---

# 🗂️ Structure du projet

```markdown
indicator-pipeline/
├── logs/
├── src/
│   ├── indicator_pipeline/
│   │   ├── __init__.py
│   │   ├── excel_to_json.py
│   │   ├── logging_config.py
│   │   ├── run_pipeline.py
│   │   ├── sftp_client.py
│   │   ├── slf_conversion.py
│   │   └── utils.py
│   │
│   └── sleeplab_converter/
│       ├── __init__.py
│       ├── edf.py
│       ├── events_mapping.py
│       └── mars_database/
│           ├── __init__.py
│           ├── annotation.py
│           ├── convert.py
│           ├── LICENSE.txt
│           └── README.md
├── .gitignore
├── pyproject.toml
├── Dockerfile
├── Snakefile
└── README.md
```

- `logs/` – Emplacement des fichiers de logs générés.
- `src/`
    - `indicator_pipeline/`
        - Contient les scripts principaux du pipeline : module principal `run_pipeline`, connexion au serveur sftp `sftp_client`, conversion des psg en .slf `slf_conversion`, dump des données ABOSA en excel dans un payload json `excel_to_json`, la configuration du logger `logging_config`, et fonctions `utils`.
    - `sleeplab_converter/`
        - Convertisseur des fichiers de polysomnographie au format sleeplab, code provenant du [repo git](https://github.com/HP2-data/sleeplab-converter-mars) `sleeplab-converter-mars`.
        - Sous module `mars_database/` comportant les modules de conversion et de traitement des fichiers d’annotations spécifiques aux appareils utilisés au labo du sommeil du CHU Grenoble.

---

# ⚙️ Installation et configuration

## 🔁 Installation en local

- Le projet est versionné sur Git et doit être cloné localement pour être utilisé :
    
    ```bash
    git clone <URL_DU_REPO>
    cd indicator-pipeline
    ```
    
- L'installation des dépendances se fait via le fichier `pyproject.toml`, qui liste tous les modules nécessaires. Il est recommandé d’utiliser un environnement virtuel (ex : `venv`) :
    
    ```bash
    python -m venv .venv
    source .venv/Scripts/activate
    pip install .
    ```
    
- Le fichier `.gitignore` exclut notamment :
    - les fichiers de logs
    - les fichiers générés par `setuptools`,
    - les fichiers temporaires ou générés automatiquement
    - les environnements virtuels (`.venv/`, etc.)
    - les fichiers générés par Snakemake (dossier `.snakemake/`, fichier _.done_ et _.flag_)

## 🐳 Montage de l’image Docker

- Le projet inclut un fichier `Dockerfile` pour permettre une **exécution isolée et reproductible** sans configuration locale.
- Construction de l’image Docker :
    
    ```bash
    docker build -t indicator-pipeline .
    ```
    
- **Sur Windows**, assurez-vous que Docker Desktop est configuré pour autoriser l’accès au disque utilisé (généralement `C:`).
- Les chemins d’accès, notamment vers les fichiers `.env`, doivent être accessibles depuis le conteneur.

## ⚙️ Configuration de l’environnement `.env`

- Le pipeline utilise un fichier `.env` pour stocker des **variables d’environnement sensibles ou spécifiques à l’environnement d’exécution**, comme les identifiants SFTP ou ou les chemins des dossiers utilisés.
- Exemple de fichier `.env` :

```bash
SFTP_HOST=mon.serveur.com
SFTP_USER=user
SFTP_KEY_PATH=pathtosshkey
SFTP_PASSWORD=motdepasse
SFTP_PORT=sftpport
ABOSA_OUTPUT_PATH=/abosa-output
LOG_OUTPUT_PATH=/app/logs
```

- Emplacement :
    - Le fichier `.env` doit être placé à la **racine du projet** (au même niveau que `pyproject.toml`).
    - Il est automatiquement chargé grâce à la librairie [`python-dotenv`](https://pypi.org/project/python-dotenv/) dans les modules concernés.
    - ⚠️ **Ne jamais versionner ce fichier** : il est ignoré par `.gitignore`.

---

# 🚀 Exécution du pipeline

⚠️ **Important** : le pipeline s'exécute en **deux temps**, avec une **étape manuelle intermédiaire**.

1. **Phase 1 – Automatique**
    
    Conversion des fichiers PSG au format *slf* (via script ou Snakemake)
    
2. **Phase 2 – Manuelle**
    
    Analyse des dossiers *slf* via le logiciel ABOSA (hors pipeline). 
    
3. **Phase 3 – Automatique**
    
    Import des résultats générés par ABOSA dans la base de données (via script ou Snakemake)
    

Cette séparation est **gérée automatiquement** dans l’exécution via Snakemake, grâce à des **fichiers de synchronisation** (`slf_conversion.done`, `abosa_complete.flag`, etc.).

⚙️ En exécution manuelle, il est de la responsabilité de l’utilisateur de **lancer les étapes une par une** et de s’assurer que l’analyse ABOSA est faite avant de poursuivre.

### 🐍 Option 1 – Exécution orchestrée via Snakemake (Recommandée)

- Le projet inclut un `Snakefile` définissant les étapes du pipeline sous forme de règles Snakemake.
- Les **volumes Docker sont générés dynamiquement** dans le `Snakefile`, en fonction de l’environnement local de l’utilisateur. Les chemins suivants sont utilisés :
    - `~/Desktop/slf-output` → dossier de sortie *slf* local
    - `~/Desktop/indicator-pipeline/logs` → fichiers de logs
    - `~/Desktop/abosa-output` → fichiers générés par ABOSA et utilisés dans la deuxième partie du pipeline
- Lancement :
    
    ```bash
    snakemake --config years="2024 2025" --cores 1
    ```
    
- L'argument `--config years="2024 2025"` permet de spécifier les années à traiter lors de l'exécution du pipeline. Si aucune année n'est précisée, **l'année en cours est utilisée par défaut**.
- Cette méthode garantit une **exécution modulaire, traçable et reproductible** des différentes étapes.
- L’exécution complète suit trois règles :
    1. `run_pipeline` : convertit les fichiers PSG au format *slf*
    2. `wait_for_manual_step` : étape manuelle via ABOSA (*cf. Calcul des indicateurs avec ABOSA*)
    3. `import_to_mars` : envoie les résultats dans la base MARS
- **Fichiers de synchronisation** (`.done`, `.flag`)
    - `slf_conversion.done` : marque la fin de l’étape de conversion (`run_pipeline`)
    - `abosa_complete.flag` : fichier **à créer manuellement** après l’analyse ABOSA pour continuer l’exécution. Un fichier `create_flag.bat` est disponible dans le répertoire pour créer ce fichier.
    - `analysis_complete.done` : marque la fin de l’import dans MARS (`import_to_mars`)
    
    Ces fichiers servent de **marqueurs d’étape** permettant à Snakemake de suivre l’avancement du pipeline. Ils sont créés ou vérifiés automatiquement par les règles, et peuvent être supprimés avec la commande lorsque tout le pipeline a été exécuté :
    
    ```bash
    snakemake clean --cores 1
    ```
    

📝 **Remarque** : les chemins par défaut du Snakefile pointent vers le **Bureau de l’utilisateur** (`~/Desktop`). Si le projet est exécuté depuis un autre emplacement, il faudra **adapter les chemins définis dans le `Snakefile` (variables `SLF_OUTPUT`, `LOGS_DIR`, etc.)** en conséquence.

### 🧪 Option 2 – Exécution manuelle (script principal)

- Commande principale pour lancer le pipeline (script principal `run_pipeline.py`)
    
    ```bash
    run-pipeline --step slf_conversion --years 2022 2023
    run-pipeline --step import_to_mars
    ```
    
- **Arguments** :
    - `--step`  : *Obligatoire*. Etape du pipeline à exécuter. Deux valeurs possibles :
        - `slf_conversion` : conversion des fichiers de polysomnographie au format *slf*.
        - `import_to_mars` : import des données produites par ABOSA dans la base MARS.
    - `--years` : *Obligatoire pour l’étape `slf_conversion` ; non requis pour `import_to_mars`.* Année(s) à traiter, chaque année correspondant à un dossier du même nom sur le serveur de stockage SFTP. Les années à traiter doivent être séparées par des espaces (ex: `--years 2024 2025`)

---

# 🦌 Calcul des indicateurs avec ABOSA

Afin de calculer les indicateurs du signal SpO₂, il faut utiliser le logiciel ABOSA manuellement. Une fois que la première étape du pipeline a été réalisée, les dossiers convertis en *slf* sont stockés dans le dossier `slf-output`, contenant un sous-dossier par année. 

### Paramètres de calcul

Une fois l’interface graphique d’ABOSA ouverte, les paramètres suivants sont à régler :

- Bouton *Select input folder* (1) ⇒ sélectionner le dossier correspondant à l’**année** à traiter `../slf-output/year`. Ce dossier doit se trouver **au même niveau que le dépôt Git** (sur le bureau, par exemple),  et **non pas à l’intérieur du dépôt**.
- Bouton *Select output folder* (2) ⇒  sélectionner le dossier de sortie. Les sorties doivent se faire dans le dossier `../abosa-output/year`.  Lui aussi doit être situé **au même niveau que le dépôt Git** (sur le bureau, par exemple). Si le dossier relatif à l’année n’existe pas encore, il faut le créer manuellement.
- Option *Input file type* (3) ⇒ cocher “*SLF”*
- Option *Artefact removal* (4) ⇒ cocher *“Yes”*

![*Interface graphique du logiciel ABOSA*](ABOSA_interface_(1).png)

*Interface graphique du logiciel ABOSA*

### Signal de saturation

Une fois les paramètres remplis, cliquer sur le bouton *“RUN”* (5). Une fenêtre s’ouvre pour choisir sur quel signal se baser pour calculer les indicateurs. Sélectionner celui correspondant à la saturation dans la liste “*primary label*” **(6), et rajouter les autres formats possibles dans la partie “*secondary labels*” (7) grâce au bouton *“Add”* (8). Les différents formats du signal de saturation sont les suivants :

- SAT
- Sp02
- SpO2
- SaO2 SaO2

Enfin, pour lancer le calcul des indicateurs, appuyer sur le bouton *“Confirm selection”* (9).

![*Interface permettant de sélectionner les labels des signaux de saturation avant de lancer les calculs*](ABOSA_interface_(2).png)

*Interface permettant de sélectionner les labels des signaux de saturation avant de lancer les calculs*

### 📃 Fichiers de sortie

Une fois les calculs des indicateurs effectués, plusieurs fichiers sont édités en sortie. Ils sont répartis en trois dossiers :

- `EventData_<date_et_heure_du_calcul>`
Regroupe les fichiers Excel contenant les événements individuels de désaturation et récupération pour chaque fichier *SLF* traité.
- `ExtraInfo_<date_et_heure_du_calcul>` 
Regroupe les fichiers texte contenant les métadonnées relatives au calcul pour chaque fichier *SLF* traité. On y retrouve les paramètres de détection et de nettoyage, les durées de sommeil par stade, les infos techniques (étiquette utilisée pour le signal SpO₂ par exemple), la détection d’artefacts, ainsi que les causes d’échec de l’analyse en cas de problème.
- `ParametersValues_<date_et_heure_du_calcul>` 
Contient un fichier Excel `ParameterValues` unique qui regroupe l'ensemble des valeurs de paramètres calculées à partir des fichiers *SLF* (une ligne par fichier PAxxxx_Vx). 
Ce dossier contient également un fichier texte `FileNotes` regroupant toutes les étiquettes de signal de saturation en oxygène saisies et le premier fichier depuis lequel l'étiquette de saturation primaire en oxygène est récupérée.

**NB** : Les données utilisées dans la deuxième partie du pipeline et intégrées dans la base de données MARS sont celles se trouvant dans le fichier `ParameterValues`.

---

# 🐍 Fonctionnement du code du pipeline

## 🔌 Connexion au serveur SFTP

**`sftp_client.py` - Client SFTP simplifié basé sur `paramiko`**

Classe utilitaire permettant d'établir une connexion SFTP et de transférer des fichiers ou dossiers entre un système local et un serveur distant.

- **Constructeur**
    
    `SFTPClient(host: str, user: str = "", key_path: str = "", password: str = "", port: int = 22)`
    
    Initialise un client SFTP avec les informations de connexion nécessaires (utilisateur, mot de passe ou clé privée, port). Ces informations sensibles sont stockées dans un fichier `.env` (cf. *Configuration de l’environnement `.env`* ci-dessus).
    Supporte l'authentification par mot de passe **ou** par clé SSH.
    
- **Méthodes**
    - `connect()`
        
        Établit une connexion au serveur SFTP distant à l’aide des identifiants fournis.
        
    - `list_files(path: str = "."): List[str]`
        
        Liste les fichiers et dossiers présents dans le répertoire `path` du serveur distant. Renvoie la liste des noms de fichiers et/ou dossiers
        
    - `is_dir(path: str): bool`
        
        Vérifie si un chemin distant correspond à un dossier.
        
    - `download_folder_recursive(remote_path: str, local_path: Path)`
        
        Télécharge récursivement tout le contenu d’un dossier distant vers un répertoire local.
        
    - `upload_folder_recursive(local_path: Path, remote_path: str)`
        
        Transfère récursivement un dossier local et tout son contenu vers un dossier distant.
        
    - `close()`
        
        Ferme proprement la connexion SFTP et libère les ressources.
        

---

## 🔄 Conversion PSG vers .slf

### Module `slf_conversion.py`

Ce module contient la classe `SLFConversion`, qui centralise la logique de conversion des enregistrements de polysomnographie au format *slf* (via l’outil `sleeplab-converter`) ainsi que leur téléversement sur le serveur SFTP distant.

- **Classe `SLFConversion`**
    
    `SLFConversion(local_slf_output: Path, remote_year_dir: PurePosixPath, sftp_client: SFTPClient)`
    Initialise un objet permettant de gérer le cycle de conversion et de transfert des fichiers *slf* pour une année donnée, en s’appuyant sur un dossier de sortie local et un chemin distant sur le serveur.
    
    **Paramètres**
    
    - `local_slf_output (Path)` : Chemin local vers le dossier de sortie *slf*, typiquement `../slf-output`.
    - `year_dir (PurePosixPath)` : Chemin distant vers le dossier d'une année spécifique sur le serveur SFTP (ex. `/.../C1/2025`).
    - `sftp_client (SFTPClient)` : Client SFTP actif permettant l'accès aux fichiers distants.
    
    **Méthodes**
    
    - `convert_folder_to_slf(local_slf_output: Path, year_dir: PurePosixPath, sftp_client: SFTPClient)`
        
        Télécharge tous les dossiers de patients pour une année donnée depuis un serveur SFTP dans un dossier temporaire local, ignorant ceux ayant déjà une sortie *slf*  existante. Les autres dossiers sont convertis au format *slf*  grâce au convertisseur `sleeplab-converter` (via la méthode `convert_dataset`).
        Les dossiers *slf* générés sont ensuite enregistrés localement dans un dossier `slf-output`, situé à l'extérieur du dépôt Git.
        
    - `upload_slf_folders_to_server(local_slf_output: Path, remote_year_dir: PurePosixPath, sftp_client: SFTPClient)`
        
        Téléverse tous les dossiers *slf* générés localement vers le répertoire distant correspondant à l’année et au numéro de patient, sur le serveur SFTP. Effectue une vérification de cohérence entre les noms de dossiers *slf* et les identifiants présents dans les fichiers *.edf* distants pour éviter toute erreur d’association.
        

### Package `sleeplab_converter`

- **Gestion des fichiers EDF** - **`edf.py`**
    
    Ce module fournit des fonctions utilitaires pour lire et extraire efficacement les données à partir des fichiers EDF (European Data Format), qui sont couramment utilisés pour stocker des enregistrements de polysomnographie.
    
    Il permet deux modes de lecture :
    
    - **Lecture directe via `pyedflib`**, pour accéder finement aux signaux et en-têtes.
    - **Lecture via la bibliothèque `MNE`**, plus robuste pour certaines annotations, mais potentiellement plus lente.
- **Package `mars-database/`**
    
    Ce package permet de faire le traitement des fichiers de polysomnographie édités par les appareils utilisés par le laboratoire du sommeil du CHU de Grenoble. 
    
    - **Module de conversion en *slf* - `convert.py`**
    Ce module permet de convertir des enregistrements de polysomnographie au format *slf* (SleepLab Format), en s’appuyant sur `sleeplab_format`. Il s’occupe également de parser les fichiers *edf* et leurs annotations associées.
    - **Traitement des fichiers d’annotation - `annotation.py`**
        
        Ce module lit, harmonise et convertit des **fichiers d’annotations de sommeil** provenant de plusieurs appareils de mesures du sommeil (*Deltamed*, *RemLogic*, *BrainRT*) afin de les rendre compatibles avec le format du convertisseur **Sleeplab**.
        
- **Mapping des événements - `events_mapping.py`**
    
    Ce module centralise les règles de correspondance (mapping) entre les événements et stades de sommeil présents dans les fichiers d’annotations issus de différents appareils de polysomnographie, et les objets structurés de la librairie `sleeplab_format`.
    
    Il permet de convertir des annotations hétérogènes (formats .csv, .txt, .rtf, etc.) en événements normalisés et exploitables par le reste du pipeline, en s’adaptant à la nomenclature propre à chaque appareil (*Deltamed*, *BrainRT* et *Remlogic*).
    

---

## 📦 Conversion Excel vers JSON

- `excel_to_json.py`
    
    Ce module extrait des données de fichiers Excel générés par ABOSA, les stocke dans des payloads au format *json*, pour ensuite les envoyer en méthode POST à une API les stockant dans la base de données MARS.
    Il maintient également un suivi des fichiers déjà traités pour éviter les doublons.
    
    - `load_processed(): Set[str]`
        
        Charge la liste des fichiers déjà traités depuis un fichier `processed.json`. Renvoie un ensemble de chemins relatifs identifiant les dossiers déjà convertis.
        
    - `save_processed(processed_set): None`
        
        Sauvegarde l’ensemble des fichiers marqués comme déjà traités dans le fichier `processed.json`.
        
    - `find_parameter_folders(abosa_output_path: Path): List[Path]`
        
        Parcourt le dossier de sortie d'ABOSA pour détecter tous les sous-dossiers contenant des données (`ParameterValues_...`). Renvoie la liste des chemins vers ces sous-dossiers.
        
    - `get_excel_from_rel_path(folder_path: Path, rel_path: str): pd.DataFrame`
        
        Charge le fichier Excel contenu dans un dossier donné. Déclenche une erreur si aucun fichier `.xlsx` n'est trouvé.
        
    - `df_to_json_payloads(df: pd.DataFrame): List[Dict[str, Any]]`
        
        Transforme chaque ligne d’un DataFrame Excel en un dictionnaire Python conforme au schéma JSON attendu :
        
        - Extraction d’identifiants patients et visites
        - Conversion numérique en *int* (entier) ou *float* (relatif) grâce à la fonction `try_parse_number(value, as_int: bool = False): Optional[Union[int, float]]` permettant d’éviter les erreurs.
        - Structuration des champs par catégories (`desaturation`, `recovery`, `ratios`, etc.) représentant les tables de MARS dans lesquelles les données seront envoyées.
        
        Renvoie une liste de dictionnaires, chacun représentant un enregistrement patient.
        
    - `excel_to_json(): None`
        
        Fonction principale du module.
        
        Elle orchestre l'ensemble du processus :
        
        - Recherche les fichiers à traiter
        - Ignore ceux déjà traités
        - Convertit les fichiers Excel en JSON
        - Sauvegarde les fichiers générés dans `logs/json_dumps`
        - Met à jour le fichier `processed.json`

---

## 🧰 Utilitaires

- `utils.py` – fonctions utilitaires communes utilisées à travers plusieurs modules
    - `parse_patient_and_visit(filename: str): Tuple[str, str]`
        
        Extrait l’identifiant du patient et le numéro de visite d’une chaîne de caractère (nom de fichier contenant les patterns *PxxxxVx* ou *Pxxxx_Vx*. 
        Renvoie un tuple contenant l’identifiant du patient et le numéro de visite sous forme de chaînes de caractère.
        
    - `extract_subject_id_from_filename(edf_file: Path): str`
        
        Extrait l’identifiant patient et le numéro de visite à partir d’un chemin de fichier edf. Renvoie une chaîne de caractère de la forme “PAxxxx_Vx” (ou “PAxxxx” si pas de numéro de visite).
        
    - `try_parse_number(value, as_int: bool = False): Optional[Union[int, float]]`
        
        Convertit une chaîne de caractère en *int* ou *float* et remplace les virgules par des points pour gérer les formats décimaux européens. Retourne le nombre ou None si la conversion échoue.
        
    - `get_repo_root(): Path`
        
        Renvoie le chemin racine du dépôt Git.
        
    - `get_local_slf_output(): Path`
        
        Renvoie le chemin complet du dossier de sortie local utilisé pour stocker les .slf (`slf-output/`).
        
    - `lowercase_extensions(dir_path: Path)`
        
        Convertit toutes les extensions des fichiers d’un dossier donné en minuscule.
        

---

## 📝 Logging

- `logging_config.py` - Utilitaires de configuration du journal (logging)
    - `setup_logging(years: List[str]): None`
        
        Configure le système de journalisation pour la pipeline en créant :
        
        - un fichier de log principal (messages de niveau INFO et plus)
        - un fichier séparé pour les avertissements et erreurs (niveau WARNING et plus)
        
        Les fichiers de log sont enregistrés dans le dossier `logs/` et leur nom contient les années sélectionnées ainsi qu’un horodatage pour garantir leur unicité.
        

---

# 📄 Ressources et annexes

- `README.md` – résumé général
- `LICENSE.txt` – licence du convertisseur [**sleeplab-converter-mars**](https://github.com/HP2-data/sleeplab-converter-mars)