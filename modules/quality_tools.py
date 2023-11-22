import os
import pandas as pd
import numpy as np
import copy
import json

class quality_tools(object):

    def __init__(self, uc):

        # Question:
        # combined forms 4&5 and 6&8 will not be separated. Switch this to string represenation instead?

        uc_tab_dict = {1:"UseCase1", 3:"UseCase3", 4:"UseCase4&5", 5:"UseCase4&5", 6:"UseCase6&8", 7:"UseCase7", 8:"UseCase6&8"}
        self.uc = uc_tab_dict[uc]

        self.dd_df = pd.read_excel(os.path.join("data", "data_dictionary.xlsx"), sheet_name=self.uc)
        self.dq_rules_df = pd.read_excel(os.path.join("data", "data_quality_rules.xlsx"), sheet_name=self.uc)

        self.uc_dict = self.get_uc_dict()
        self.config_dict = self.get_config_dict()

        return None

    def get_uc_dict(self):
        dd_df = self.dd_df[self.dd_df[["variable"]].notnull().all(1)].copy()

        if self.dq_rules_df.empty:
            dq_rules_df = self.dq_rules_df
        else:
            dq_rules_df = self.dq_rules_df[self.dq_rules_df[["variable"]].notnull().all(1)].copy()

        properties = list(dd_df["variable"].unique())

        uc_dict = {}

        for property in properties:
            if property in dd_df["variable"].unique():
                property_df = dd_df[dd_df["variable"]==property]
                if len(property_df) > 0:
                    property_ser = property_df.iloc[0]

                    uc_dict[property] = {}
                    uc_dict[property]['name'] = property
                    uc_dict[property]['group'] = property_ser["group"]
                    if not pd.isnull(property_ser["matrix"]):
                        uc_dict[property]['matrix'] = property_ser["matrix"]
                        uc_dict[property]['matrix_parent'] = True if property_ser["matrix_parent"] == 1 else False
                        uc_dict[property]['matrix_start'] = True if property_ser["matrix_start"] == 1 else False
                        uc_dict[property]['matrix_end'] = True if property_ser["matrix_end"] == 1 else False
                    uc_dict[property]['required'] = property_ser["required"]
                    uc_dict[property]['req_condition'] = property_ser["req_condition"] if not pd.isnull(property_ser["req_condition"]) else ''
                    uc_dict[property]['minimal'] = property_ser["minimal"] if not pd.isnull(property_ser["minimal"]) else 'No'
                    uc_dict[property]['mandatory'] = property_ser["mandatory"] if not pd.isnull(property_ser["mandatory"]) else 'No'
                    uc_dict[property]['output_type'] = property_ser["output_type"]
                    uc_dict[property]['display_type'] = property_ser["display_type"]
                    uc_dict[property]['display_label'] = property_ser["display_label"]
                    uc_dict[property]['note'] = property_ser["note"] if not pd.isnull(property_ser["note"]) else ''

                    code_dict = {}
                    if not pd.isnull(property_ser["code_list"]):
                        code_dict = self.parse_code_dict(property_ser["code_list"], property_ser["code_default"])
                    uc_dict[property]['permissible_values'] = code_dict

                    if dq_rules_df.empty:
                        quality_df = dq_rules_df
                    else:
                        quality_df = dq_rules_df[dq_rules_df["variable"]==property]
                    
                    quality_dict = {}
                    for index, row in quality_df.iterrows():
                        quality_dict[row.check] = {}
                        quality_dict[row.check]['dimension'] = row.check_dimension
                        quality_dict[row.check]['check_type'] = row.check_type
                        if row.check_type in ['range','length']:
                            if not pd.isnull(property_ser["min"]):
                                quality_dict[row.check]['value_min'] = property_ser["min"]
                            if not pd.isnull(property_ser["max"]):
                                quality_dict[row.check]['value_max'] = property_ser["max"]
                        quality_dict[row.check]['message'] = row.message
                    uc_dict[property]['quality_rules'] = quality_dict

        json_str = json.dumps(uc_dict, indent=4)

        with open(os.path.join(os.path.join("data","test") ,f"test_uc.json"), "w") as outfile:
            outfile.write(json_str)

        return uc_dict

    def get_config_dict(self):

        groups_dict = {}

        for key in self.uc_dict.keys():
            rec = self.uc_dict[key]
            if rec['group'] not in groups_dict.keys():
                groups_dict[rec['group']] = {}
                groups_dict[rec['group']]['properties'] = []

            property_dict = {}
            property_dict['name'] = rec['name']
            if 'matrix' in rec:
                property_dict['matrix'] = rec['matrix']
                property_dict['matrix_parent'] = rec['matrix_parent']
                property_dict['matrix_start'] = rec['matrix_start']
                property_dict['matrix_end'] = rec['matrix_end']
            property_dict['required'] = rec['required']
            property_dict['req_condition'] = rec['req_condition']
            property_dict['minimal'] = rec['minimal']
            property_dict['mandatory'] = rec['mandatory']
            property_dict['output_type'] = rec['output_type']
            property_dict['display_type'] = rec['display_type']
            property_dict['display_label'] = rec['display_label']
            property_dict['note'] = rec['note']
            property_dict['permissible_values'] = rec['permissible_values']

            groups_dict[rec['group']]['properties'].append(property_dict)

        config_dict = {}
        config_dict['groups'] = []

        for key in groups_dict.keys():
            group_dict = {}
            group_dict['name'] = key
            group_dict['properties'] = groups_dict[key]['properties']
            config_dict['groups'].append(group_dict)

        json_str = json.dumps(config_dict, indent=4)

        with open(os.path.join(os.path.join("data","test") ,f"test_config.json"), "w") as outfile:
            outfile.write(json_str)

        return config_dict

    def check_quality(self, dict):

        result_dict = {}

        for check_key in dict.keys():

            check_value = dict[check_key]
            
            value_info = self.uc_dict[check_key]

            result_dict[check_key] = self.validate_values(check_key, check_value, value_info)

        json_str = json.dumps(result_dict, indent=4)

        with open(os.path.join(os.path.join("data","test") ,f"test_results.json"), "w") as outfile:
            outfile.write(json_str)

        return result_dict

    def validate_values(self, key, value, info):

        required = info["required"]
        req_condition = info["req_condition"]
        minimal = info["minimal"]
        mandatory = info["mandatory"]
        type = info["output_type"]
        rules = info["quality_rules"]

        rule_results = {"pass":[], "fail":[]}

        for rule_key in rules.keys():

            validate = {}
            validate["check_name"] = rule_key
            validate["check_variable"] = key
            validate["check_dimension"] = rules[rule_key]["dimension"]
            validate["check_type"] = rules[rule_key]["check_type"]
            validate["check_message"] = rules[rule_key]["message"]

            if "value_min" in rules[rule_key]:
                validate["value_min"] = rules[rule_key]["value_min"]

            if "value_max" in rules[rule_key]:
                validate["value_max"] = rules[rule_key]["value_max"]

            check_type = rules[rule_key]["check_type"]
            if check_type == "minimal_req":
                
                if minimal == 'Yes':
                    if value == '' or value == None or value == -1:
                        rule_results["fail"].append(validate)
                    else:
                        rule_results["pass"].append(validate)
                else:
                    rule_results["pass"].append(validate)

            elif check_type == "mandatory_req":

                if mandatory == 'Yes':
                    if value == '' or value == None or value == -1:
                        rule_results["fail"].append(validate)
                    else:
                        rule_results["pass"].append(validate)
                else:
                    rule_results["pass"].append(validate)

            elif check_type == "length":

                if len(value) > rules[rule_key]["value_max"]:
                    rule_results["fail"].append(validate)
                else:
                    rule_results["pass"].append(validate)

            elif check_type == "datatype":
                d='d'
            elif check_type == "permissible":
                d='d'
            elif check_type == "range":

                if value > rules[rule_key]["value_max"] \
                    or value < rules[rule_key]["value_min"]:
                    rule_results["fail"].append(validate)
                else:
                    rule_results["pass"].append(validate)

        return rule_results
        
    def get_config_file(self, path):
        """ 
        Creates a Config in the specified path for the active use case.
            
        :param path: Path for output

        :return: -> None
        """
      
        json_str = json.dumps(self.config_dict, indent=4)

        with open(os.path.join(path,f"{self.uc}.json"), "w") as outfile:
            outfile.write(json_str)

        return None
        
    def parse_code_list(self, code_string):

        codes = code_string.split(" | ")

        code_list = []
        #code_list.append({"value": -1, "display": "Select:"})

        for code in codes:
            elements = code.split("; ")
            code_element = {}
            code_element["value"] = int(elements[0])
            code_element["display"] = elements[1]
            code_list.append(code_element)

        return code_list
    
    def parse_code_dict(self, code_string, code_default):

        codes = code_string.split(" | ")

        code_dict = {}
        #code_dict[-1] = {"display": "Select:"}

        for code in codes:
            elements = code.split("; ")
            code_dict[int(elements[0])] = {}
            code_dict[int(elements[0])]["display"] = elements[1]
            if not pd.isnull(code_default) and int(elements[0]) == int(code_default):
                code_dict[int(elements[0])]["default"] = True

        return code_dict









    #def get_config_dict(self):

    #    config_df = self.dd_df[self.dd_df[["variable"]].notnull().all(1)].copy()

    #    groups = list(config_df["group"].unique())
    #    if "Form Status" in groups:
    #        groups.remove("Form Status")
    #    if np.nan in groups:
    #        groups.remove(np.nan)
    #    concepts = list(config_df["variable"].unique())

    #    config_dict = {}
    #    config_dict['groups'] = []

    #    for group in groups:
    #        group_df = config_df[config_df["group"]==group]

    #        group_dict = {}
    #        group_dict['name'] = group
    #        group_dict["properties"] = []

    #        for concept in concepts:
    #            if concept in group_df["variable"].unique():
    #                concept_df = group_df[group_df["variable"]==concept]
    #                if len(concept_df) > 0:
    #                    concept_ser = concept_df.iloc[0]

    #                    concept_dict = {}
    #                    concept_dict['name'] = concept
    #                    if not pd.isnull(concept_ser["matrix"]):
    #                        concept_dict['matrix'] = concept_ser["matrix"]
    #                        if concept_ser["matrix_parent"] == 1:
    #                            concept_dict['matrix_parent'] = True 
    #                    concept_dict['required'] = concept_ser["required"]
    #                    concept_dict['req_condition'] = concept_ser["req_condition"] if not pd.isnull(concept_ser["req_condition"]) else ''
    #                    concept_dict['minimal'] = concept_ser["minimal"] if not pd.isnull(concept_ser["minimal"]) else 'No'
    #                    concept_dict['mandatory'] = concept_ser["mandatory"] if not pd.isnull(concept_ser["mandatory"]) else 'No'
    #                    concept_dict['output_type'] = concept_ser["output_type"]
    #                    concept_dict['display_type'] = concept_ser["display_type"]
    #                    concept_dict['display_label'] = concept_ser["display_label"]
    #                    concept_dict['note'] = concept_ser["note"] if not pd.isnull(concept_ser["note"]) else ''

    #                    code_dict = {}
    #                    if not pd.isnull(concept_ser["code_list"]):
    #                        code_dict = self.parse_code_dict(concept_ser["code_list"], concept_ser["code_default"])
    #                    concept_dict['permissible_values'] = code_dict

    #                group_dict["properties"].append(concept_dict)

    #        config_dict['groups'].append(group_dict)
      
    #    json_str = json.dumps(config_dict, indent=4)

    #    with open(os.path.join(os.path.join("data","test") ,f"test_config.json"), "w") as outfile:
    #        outfile.write(json_str)

    #    return config_dict






    #def get_permissible_values(self, item, sort=True):
    #    """ 
    #    Returns a dictionary of permissible values (code, display)
            
    #    :param item: The data item that the list is being retrieved for
    #    :param sort: True/False whether it should be sorted by display value

    #    :return: -> dict[code]["display"]
    #    """
    #    item_df = self.dd_df[self.dd_df.csv_col == item].copy()
    #    item_df = item_df[["csv_val","value"]]
    #    item_df.rename(columns={"csv_val": "code", "value": "display"}, inplace=True)
    #    item_df.set_index("code", drop=True, inplace=True)

    #    if sort == True:
    #        item_df.sort_values(by="display", inplace=True)

    #    item_dict = item_df.to_dict(orient="index")

    #    return item_dict



    #def get_config_file_old(self, path):
    #    """ 
    #    Returns a dictionary of all use case elements
            
    #    :return: -> dict[code]["display"]
    #    """
    #    config_df = self.dd_df[self.dd_df[['csv_col']].notnull().all(1)].copy()
    #    #config_df = config_df[["","","",""]]

    #    groups = config_df.group.unique()
    #    concepts = config_df.csv_col.unique()

    #    for group in groups:
    #        group_df = config_df[config_df.group==group]

    #        group_dict = {}
    #        group_dict[group] = {}
    #        #group_dict[group]["bsonType"] = "object"
    #        group_dict[group]["properties"] = {}

    #        for concept in concepts:
    #            if concept in group_df.csv_col.unique():
    #                group_dict[group]["properties"][concept] = {}

    #                concept_df = group_df[group_df.csv_col==concept]

    #                if len(concept_df) > 1:
    #                    a='a'

    #                pos = 0
    #                values = {}
    #                for index, row in concept_df.iterrows():
                        
    #                    if pos == 0:
    #                        output_type = None
    #                        display_type = None

    #                        if row.type == 'S':
    #                            output_type = 'string'
    #                            display_type = 'textbox'
    #                        elif row.type == 'C':
    #                            output_type = 'int'
    #                            display_type = 'dropdown'
    #                        elif row.type == 'I':
    #                            output_type = 'int'
    #                            display_type = 'textbox'
    #                        elif row.type == 'B':
    #                            output_type = 'bool'
    #                            display_type = 'checkbox'

    #                        group_dict[group]["properties"][concept]["output_type"] = output_type
    #                        group_dict[group]["properties"][concept]["display_type"] = display_type
    #                        group_dict[group]["properties"][concept]["display_label"] = row.concept

    #                    if row.type == 'C':
    #                        val = int(row.csv_val)
    #                        values[val] = {}
    #                        values[val]['display'] = row.value

    #                    pos += 1

    #                group_dict[group]["properties"][concept]["values"] = values

    #        json_str = json.dumps(group_dict, indent=4)

    #        with open(os.path.join(path,f"{group}.json"), "w") as outfile:
    #            outfile.write(json_str)

    #    return None





    #def get_config_file(self, path):
    #""" 
    #Creates a Config in the specified path for the active use case.
            
    #:param path: Path to output to

    #:return: -> None
    #"""
    #config_df = self.dd_df[self.dd_df[["Variable/Field Name"]].notnull().all(1)].copy()

    #groups = list(config_df["Section"].unique())
    #if "Form Status" in groups:
    #    groups.remove("Form Status")
    #if np.nan in groups:
    #    groups.remove(np.nan)
    #concepts = list(config_df["Variable/Field Name"].unique())

    #uc_dict = {}
    #uc_dict['groups'] = []

    #for group in groups:
    #    group_df = config_df[config_df["Section"]==group]

    #    group_dict = {}
    #    group_dict['name'] = group
    #    group_dict["properties"] = []

    #    for concept in concepts:
    #        if concept in group_df["Variable/Field Name"].unique():
    #            concept_df = group_df[group_df["Variable/Field Name"]==concept]
    #            if len(concept_df) > 0:
    #                concept_ser = concept_df.iloc[0]

    #                concept_dict = {}
    #                concept_dict['name'] = concept
    #                concept_dict['required'] = concept_ser["Required"]
    #                concept_dict['output_type'] = concept_ser["Validation Type"] if not pd.isnull(concept_ser["Validation Type"]) else 'integer'
    #                concept_dict['display_type'] = concept_ser["Field Type"]
    #                concept_dict['display_label'] = concept_ser["Label"]
    #                concept_dict['note'] = concept_ser["Field Note"] if not pd.isnull(concept_ser["Field Note"]) else ''

    #                if not pd.isnull(concept_ser["Code"]):
    #                    code_list = self.parse_code_list(concept_ser["Code"])
    #                    concept_dict['permissible_values'] = code_list

    #            group_dict["properties"].append(concept_dict)

    #    uc_dict['groups'].append(group_dict)

      
    #json_str = json.dumps(uc_dict, indent=4)

    #with open(os.path.join(path,f"{self.uc}.json"), "w") as outfile:
    #    outfile.write(json_str)

    #return None