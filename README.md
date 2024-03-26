# EuCanImage Redcap Quality Tools
===============================

# Configuration file

An example configuration is avaialble at [/example/config.json.example](https://github.com/michael-rutherford/eucanimage-redcap-quality-tools/blob/master/example/config_example.json).

The JSON file contains the following parameters:

## Parameters for Redcap API Processing:

* **redcap_server**: 
    * The URL of the Redcap server.
* **redcap_forms**: 
    * A list of the Redcap forms to be processed.
        * [ "use_case_1", "use_case_3", "use_case_4_and_5", "use_case_6_and_8", "use_case_7" ]
* **redcap_dags**: 
    * A list of data access groups **(INFO ONLY - NOT USED)**
* **redcap_tokens**: 
    * Your API security tokens for each redcap form.

## Parameters for Local File Processing:

**Please Note:** if bypass_recap is set to true, the redcap parameters above will be ignored.

* **bypass_redcap**: 
    * Set to true for processing local files.
* **bypass_dag**: 
    * The data access group being assessed. (Ex. "umu" for Umeå University)
* **bypass_files**: 
    * The file path for Redcap formated CSVs for each use cases.
        * *Enter "" if unused*

*These local file parameters do not need to exist for the process to run. (works with old config files)*

## Other Required parameters:

* **rule_weights**: 
    * A list of the weights for each rule.
* **data_dictionary_path**: 
    * The path to the [data dictionary file](https://github.com/michael-rutherford/eucanimage-redcap-quality-tools/blob/master/data/data_dictionary.xlsx).
* **data_quality_rules_path**: 
    * The path to the [data quality rules file](https://github.com/michael-rutherford/eucanimage-redcap-quality-tools/blob/master/data/data_quality_rules.xlsx).
* **output_path**: 
    * The path to put output files.
* **log_path**: 
    * The path to put log files.
* **log_level**: 
    * The level of logging to use. Options are: debug, info, warning, error, critical


===============================

# Steps to Run

1. Setup environment using [requirements.txt](https://github.com/michael-rutherford/eucanimage-redcap-quality-tools/blob/master/requirements.txt)
2. Copy config and update the following parameters: 
    * redcap tokens (for API) **or** bypass_dag and bypass_files (for local)
    * data dictionary path (copy or direct to file in /data folder)
    * data quality rules path (copy or direct to file in /data folder)
    * output path (for db and output files)
    * log path (for logs)
3. Run script
    ```

    python3 run_quality_checks.py <path to config_file>

    ```

