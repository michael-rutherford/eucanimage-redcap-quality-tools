# EuCanImage Redcap Quality Tools
===============================

# Configuration file

An example configurate is avaialble at [/example/config.json.example](https://github.com/michael-rutherford/eucanimage-redcap-quality-tools/blob/master/example/config_example.json).

The configuration file is a JSON file that contains the following information:

* **redcap_server**: The URL of the Redcap server.
* **redcap_forms**: A list of the Redcap forms that are to be processed.
* **redcap_dags**: A list of data access groups **(NOT USED)**
* **redcap_tokens**: Your security tokens for all redcap forms.
* **rule_weights**: A list of the weights for each rule.
* **data_dictionary_path**: The path to the [data dictionary file](https://github.com/michael-rutherford/eucanimage-redcap-quality-tools/blob/master/data/data_dictionary.xlsx).
* **data_quality_rules_path**: The path to the [data quality rules file](https://github.com/michael-rutherford/eucanimage-redcap-quality-tools/blob/master/data/data_quality_rules.xlsx).
* **output_path**: The path to the output files.
* **log_path**: The path to put log files.
* **log_level**: The level of logging to use. The options are: debug, info, warning, error, critical.

===============================

# Steps to Run

1. Setup environment using [requirements.txt](https://github.com/michael-rutherford/eucanimage-redcap-quality-tools/blob/master/requirements.txt)
2. Copy and update configuration 
    a. redcap tokens
    b. data dictionary path (from /data folder)
    c. data quality rules path (from /data folder)
    d. output path
    e. log path
3. Run script
    ```

    python3 redcap_quality_tools.py <path to config_file>

    ```

