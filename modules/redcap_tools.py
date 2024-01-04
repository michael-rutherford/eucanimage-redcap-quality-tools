import os
from re import S
from numpy import datetime_as_string
import requests
import pandas as pd
import json
from datetime import datetime

from models.redcap_db import redcap_db
from models.redcap_db import RedcapRecord
from models.redcap_db import QualityRuleWeight
from models.redcap_db import QualityAssessment
from models.redcap_db import QualityAssessmentResult

class redcap_tools(object):

    def __init__(self, args, log):
        
        self.args = args
        self.log = log
        
        if not os.path.exists(args["output_path"]):
            os.makedirs(args["output_path"])

        db_connect_string = f'sqlite+pysqlite:///{os.path.join(args["output_path"],"data_quality_results.db")}'
        self.redcap_db = redcap_db(db_connect_string)
        self.db_session = self.redcap_db.get_session()
        
        self.dq_dict = None
        
    def refresh(self, refresh_all):

        if refresh_all == True:
            self.redcap_db.drop_database(True)
            self.redcap_db.create_database(True)
            self.organize_dq_rules()
            self.retrieve_data_records()  
            self.generate_dq_dict()
        else:
            self.redcap_db.drop_table("quality_assessment")
            self.redcap_db.drop_table("quality_assessment_result")
            self.redcap_db.drop_table("quality_assessment_score")
            self.redcap_db.create_database(True)
            self.generate_dq_dict()            
            
        return None
        
    def organize_dq_rules(self):
        
        args = self.args
        log = self.log

        log.info(f'Organizing Data Quality Rules')
        
        dd_path = args['data_dictionary_path']
        dq_path = args['data_quality_rules_path']
        
        uc_dd_dfs = []
        uc_dq_dfs = []
        
        uc_dict = {"UseCase1":"use_case_1", "UseCase3":"use_case_3", 
                   "UseCase4&5":"use_case_4_and_5", "UseCase7":"use_case_7", 
                   "UseCase6&8":"use_case_6_and_8"}
        
        for tab in uc_dict.keys():
            uc = uc_dict[tab]
            log.info(f'---- {uc}')

            dd_df = pd.read_excel(dd_path, sheet_name=tab)
            dd_df['uc'] = uc
            #dd_df.rename(columns={'min':'range_min', 'max':'range_max'})
            uc_dd_dfs.append(dd_df)
            
            dq_df = pd.read_excel(dq_path, sheet_name=tab)
            dq_df['uc'] = uc
            #dq_df.rename(columns={'min':'range_min', 'max':'range_max'})
            uc_dq_dfs.append(dq_df)

        dd_df = pd.concat(uc_dd_dfs)
        dq_df = pd.concat(uc_dq_dfs)
        
        self.redcap_db.insert_dataframe(self.db_session, 'data_dictionary', dd_df)
        self.redcap_db.insert_dataframe(self.db_session, 'quality_rule', dq_df)
        
        log.info(f'Importing Weights')
        
        rule_weights = args['rule_weights']
        insert_weights = []
        for key, value in rule_weights.items():
            rule_weight = QualityRuleWeight()
            rule_weight.check_type = key
            rule_weight.weight = value
            insert_weights.append(rule_weight)
            
        self.redcap_db.insert_list(self.db_session, insert_weights)            
        
        return None

    def generate_dq_dict(self):
        
        def parse_code_list(code_string):

            codes = code_string.split(" | ")

            code_dict = {}

            for code in codes:
                elements = code.split("; ")
                code_dict[int(elements[0])] = elements[1]

            return code_dict

        args = self.args
        log = self.log

        log.info(f'Generating Data Quality Dictionary')
        
        dq_dict = {}

        uc_dict = {"UseCase1":"use_case_1", "UseCase3":"use_case_3", 
                   "UseCase4&5":"use_case_4_and_5", "UseCase7":"use_case_7", 
                   "UseCase6&8":"use_case_6_and_8"}
        
        for tab in uc_dict.keys():
            uc = uc_dict[tab]
            #log.info(f'---- {uc}')
            
            dq_query = f"select * from quality_rule where uc = '{uc}'"
            dq_df = self.redcap_db.query(self.db_session, 'quality_rule', dq_query, return_df=True)

            dq_dict[uc] = {}
            
            for index, row in dq_df.iterrows():
                variable = row['variable']
                check_type = row['check_type']
                
                if variable not in dq_dict[uc]:
                    dq_dict[uc][variable] = {} 
                dq_dict[uc][variable][check_type] = {}
                dq_dict[uc][variable][check_type]['check_name'] = row['check']
                dq_dict[uc][variable][check_type]['check_dimension'] = row['check_dimension']
                dq_dict[uc][variable][check_type]['check_message'] = row['message']
                
                if check_type == 'datatype':
                    dq_dict[uc][variable][check_type]['check_datatype'] = row['datatype']
                if check_type in ['minimal_req','mandatory_req']:
                    dq_dict[uc][variable][check_type]['check_required'] = row['required']
                    dq_dict[uc][variable][check_type]['check_condition'] = row['req_condition']
                if check_type == 'range':
                    dq_dict[uc][variable][check_type]['check_min'] = row['min']
                    dq_dict[uc][variable][check_type]['check_max'] = row['max']
                if check_type == 'permissible':
                    code_dict = {}
                    if not pd.isnull(row['code_list']):
                        code_dict = parse_code_list(row['code_list'])
                    dq_dict[uc][variable][check_type]['check_values'] = code_dict

        self.dq_dict = dq_dict
        
        return None

    def retrieve_data_records(self):
        
        def export_records(redcap_form):

            data = {
                'token': self.args["redcap_tokens"][redcap_form],
                'content': 'record',
                'action': 'export',
                'format': 'json',
                'type': 'flat',
                'csvDelimiter': '',
                'rawOrLabel': 'raw',
                'rawOrLabelHeaders': 'raw',
                'exportCheckboxLabel': 'false',
                'exportSurveyFields': 'false',
                'exportDataAccessGroups': 'true',
                'returnFormat': 'json'
            }
            response = requests.post(self.args["redcap_server"],data=data)
            response_status = response.status_code
            response_json = response.json()
    
            return response_json

        args = self.args
        log = self.log

        log.info(f'Retrieving Data Records')

        for redcap_form in args['redcap_forms']:

            log.info(f'---- {redcap_form}')

            record_list = []

            # get list of records
            log.info(f'Retrieving')
            records = export_records(redcap_form)
            records = [{**d, "redcap_form": redcap_form} for d in records]
            
            log.info(f'Organizing')
            for record in records:
                rec = RedcapRecord()
                rec.redcap_form = redcap_form
                rec.redcap_data_access_group = record['redcap_data_access_group'] if 'redcap_data_access_group' in record else 'test'
                rec.redcap_record_id = record['record_id']
                rec.redcap_data = json.dumps(record)
                record_list.append(rec)

            log.info(f'Writing')
            self.redcap_db.insert_list(self.db_session, record_list)

        return None

    def run_quality_checks(self):
        
        def run_record_quality_check(record):

            def run_value_quality_check(record, record_info, key, value):
                
                def check_value_datatype(value, datatype):
                        
                    if value is None or value == '' or pd.isnull(value):    
                        return True
                    else:
                        if datatype == 'integer':
                            try:
                                value = int(value)
                            except:
                                return False
                        elif datatype == 'number':
                            try:
                                value = float(value)
                            except:
                                return False
                        elif datatype == 'date':
                            try:
                                value = datetime.strptime(value, '%Y-%m-%d')
                            except:
                                return False
                        elif datatype == 'datetime':
                            try:
                                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                            except:
                                return False
                        elif datatype == 'time':
                            try:
                                value = datetime.strptime(value, '%H:%M:%S')
                            except:
                                return False
                        elif datatype == 'string':
                            try:
                                value = str(value)
                            except:
                                return False
                        elif datatype == 'boolean':
                            try:
                                value = bool(value)
                            except:
                                return False
                        else:
                            return False
                        
                        return True

                def check_value_range(value, value_min, value_max):
                        
                    if value is None or value == '' or pd.isnull(value):
                        return True                        
                    elif int(value) >= int(value_min) and int(value) <= int(value_max):
                        return True
                    else:
                        return False
                    
                def check_value_permissible(value, permissible_values):
                    
                    if value is None or value == '' or pd.isnull(value):
                        return True
                    elif int(value) in permissible_values.keys():
                        return True
                    else:
                        return False

                def check_value_required(record, value, condition):
                        
                    if condition == '' or pd.isnull(condition):                    
                        if value is None or value == '' or pd.isnull(value):
                            return False
                        else:
                            return True
                    else:
                        if "> 13" in condition or "<= 13" in condition:
                            condition_string = condition.replace("[","int(record['").replace("]","'])")
                            if 'chemo_drug_5' in condition_string:
                                condition_string = "(record['chemo_drug_5'] != '') and " + condition_string
                            elif 'chemo_drug_4' in condition_string:
                                condition_string = "(record['chemo_drug_4'] != '') and " + condition_string
                            elif 'chemo_drug_3' in condition_string:
                                condition_string = "(record['chemo_drug_3'] != '') and " + condition_string
                            elif 'chemo_drug_2' in condition_string:
                                condition_string = "(record['chemo_drug_2'] != '') and " + condition_string
                            elif 'chemo_drug' in condition_string:
                                condition_string = "(record['chemo_drug'] != '') and " + condition_string
                        elif condition == "(([histopat]<>'' AND [histopat]<5) OR ([histopat_2]<>'' AND [histopat_2]<5) OR ([histopat_3]<>'' AND [histopat_3]<5))":
                            condition_string = "((record['histopat'] != '' and int(record['histopat']) < 5) or (record['histopat_2'] != '' and int(record['histopat_2']) < 5) or (record['histopat_3'] != '' and int(record['histopat_3']) < 5))"
                        else:
                            condition_string = condition.replace("[","record['").replace("]","']").replace(" = "," == ").replace("AND","and").replace("OR","or").replace("<>","!=")
                        
                        is_required = eval(condition_string)

                        if is_required:
                            if value is None or value == '' or pd.isnull(value):
                                return False
                            else:
                                return True                    
                        else:
                            return True

                check_dict = self.dq_dict[record_info['redcap_form']][key] if key in self.dq_dict[record_info['redcap_form']] else {}
                
                check_results = []

                for check_type in check_dict.keys():
                    check_result = record_info.copy()
                    
                    check_result['variable'] = key
                    check_result['check_type'] = check_type
                    check_result['check_name'] = check_dict[check_type]['check_name']
                    check_result['check_dimension'] = check_dict[check_type]['check_dimension']
                    check_result['check_value'] = value

                    if check_type == 'datatype':                        
                        check_result['check_passed'] = check_value_datatype(value, check_dict[check_type]['check_datatype'])
                        check_result['check_message'] = check_dict[check_type]['check_message'] if not check_result['check_passed'] else ''
                    elif check_type == 'range':
                        check_result['check_passed'] = check_value_range(value, check_dict[check_type]['check_min'], check_dict[check_type]['check_max'])
                        check_result['check_message'] = check_dict[check_type]['check_message'] if not check_result['check_passed'] else ''
                    elif check_type == 'permissible':
                        check_result['check_passed'] = check_value_permissible(value, check_dict[check_type]['check_values'])
                        check_result['check_message'] = check_dict[check_type]['check_message'] if not check_result['check_passed'] else ''
                    elif check_type == 'minimal_req':
                        check_result['check_passed'] =  check_value_required(record, value, check_dict[check_type]['check_condition'])
                        check_result['check_message'] = check_dict[check_type]['check_message'] if not check_result['check_passed'] else ''
                    elif check_type == 'mandatory_req':
                        check_result['check_passed'] =  check_value_required(record, value, check_dict[check_type]['check_condition'])
                        check_result['check_message'] = check_dict[check_type]['check_message'] if not check_result['check_passed'] else ''
                    else:
                        pass
                    
                    check_results.append(check_result)
                    
                return check_results    
        
            results = []
            record_info = {}
            record_info['redcap_form'] = record['redcap_form'] 
            record_info['redcap_data_access_group'] = record['redcap_data_access_group'] if 'redcap_data_access_group' in record else 'test'
            record_info['redcap_record_id'] = record['record_id']
            
            for key in record.keys():
                results.extend(run_value_quality_check(record, record_info, key, record[key]))

            return results

        args = self.args
        log = self.log

        log.info(f'Running Data Quality Checks')
            
        result_list = []
        
        rec_query = "select * from redcap_record"
        records = self.redcap_db.query(self.db_session, RedcapRecord, rec_query, return_df=False)

        for record in records:
            results = run_record_quality_check(json.loads(record.redcap_data))
            #result_list.extend(results)
            self.redcap_db.insert_dicts(self.db_session, 'quality_assessment', results)

        #self.result_list = result_list
        
        return None

    def get_quality_results(self):
        
        args = self.args
        log = self.log

        log.info(f'Getting Data Quality Results')        
        
        # get list of forms
        try:
            qar_query = """
                with passed_counts as
                (
	                select redcap_form,
	                       redcap_data_access_group,
	                       redcap_record_id,
	                       check_dimension,
	                       check_type,
	                       count(qa_id) as total_checks,
	                       sum(check_passed) as passed_checks
	                from quality_assessment
	                group by redcap_form, redcap_data_access_group, 
	                         redcap_record_id, check_dimension, check_type
                ),
                passed_results as
                (
	                select qac.*, qrw.weight as weight,
 	                       CAST(qac.passed_checks AS REAL) / qac.total_checks as score,
 	                       CAST(qac.passed_checks AS REAL) / qac.total_checks * qrw.weight as weighted_score
	                from passed_counts qac
	                left join quality_rule_weight qrw
	                on qac.check_type = qrw.check_type
                )
                insert into quality_assessment_result (redcap_form, redcap_data_access_group, 
                    redcap_record_id, check_dimension, check_type, total_checks, passed_checks,
                    weight, score, weighted_score)
                select * from passed_results
            """
            self.db_session.execute(qar_query)
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            print(f"An error occurred: {e}")
            
        return None

    def get_quality_scores(self):

        args = self.args
        log = self.log

        log.info(f'Getting Quality Scores')
        
        dim_list = self.redcap_db.query(session=self.db_session, query_text="select distinct check_dimension from quality_rule", return_df=True)["check_dimension"].tolist()            
        type_list = self.redcap_db.query(session=self.db_session, query_text="select distinct check_type from quality_rule", return_df=True)["check_type"].tolist()   
        weights_dict = self.redcap_db.query(session=self.db_session, query_text="select distinct check_type, weight from quality_rule_weight", return_df=True).set_index('check_type',drop=True).to_dict(orient='index')
        weight_dict = {key: value['weight'] for key, value in weights_dict.items()}

        score_inserts = []

        def get_score(form=None, dag=None, rec=None):

            result_level = ""
            qa_query = "select * from quality_assessment where 1=1"
            qas_query = "select * from quality_assessment_result where 1=1"
            if form is not None:
                qa_query += f" and redcap_form = '{form}'"
                qas_query += f" and redcap_form = '{form}'"
                result_level += "form"
            if dag is not None:
                qa_query += f" and redcap_data_access_group = '{dag}'"
                qas_query += f" and redcap_data_access_group = '{dag}'"
                result_level += "_dag"
            if rec is not None:
                qa_query += f" and redcap_record_id = '{rec}'"
                qas_query += f" and redcap_record_id = '{rec}'"
                result_level += "_rec"
                
            qa_df = self.redcap_db.query(session=self.db_session, query_text=qa_query, return_df=True)
            qas_df = self.redcap_db.query(session=self.db_session, query_text=qas_query, return_df=True)

            score_insert = {}
            score_insert['result_level'] = result_level
            score_insert['redcap_form'] = form
            score_insert['redcap_data_access_group'] = dag
            score_insert['redcap_record_id'] = rec
            
            for dim in dim_list:
                dim_df = qas_df[qas_df['check_dimension'] == dim]
                dim_total = dim_df['total_checks'].sum()
                dim_passed = dim_df['passed_checks'].sum()
                dim_score = dim_passed / dim_total if dim_total > 0 else 1
                score_insert[f'{dim}_score'] = dim_score

            weighted_score = 0
            
            for check_type in type_list:
                check_df = qas_df[qas_df['check_type'] == check_type]
                check_total = check_df['total_checks'].sum()
                check_passed = check_df['passed_checks'].sum()
                check_score = check_passed / check_total if check_total > 0 else 1
                score_insert[f'{check_type}_score'] = check_score
                
                check_weighted = check_score * weight_dict[check_type]
                weighted_score += check_weighted

            score_insert['weighted_score'] = weighted_score
            
            total_checks = qas_df['total_checks'].sum()
            passed_checks = qas_df['passed_checks'].sum()
            total_score = passed_checks / total_checks if total_checks > 0 else 1
            score_insert['total_score'] = total_score
            
            json_dict = {}
            json_dict['score'] = score_insert
            json_dict['weight'] = weight_dict
            json_dict['assessment'] = qa_df.to_dict(orient='index')
            
            score_insert['export_json'] = json.dumps(json_dict)

            return score_insert

        form_query = "select distinct redcap_form from redcap_record"
        form_list = self.redcap_db.query(session=self.db_session, query_text=form_query, return_df=True)["redcap_form"].tolist()
        for form in form_list:
            score_inserts.append(get_score(form=form))
            dag_query = f"select distinct redcap_data_access_group from redcap_record where redcap_form = '{form}'"
            dag_list = self.redcap_db.query(session=self.db_session, query_text=dag_query, return_df=True)["redcap_data_access_group"].tolist()
            for dag in dag_list:
                score_inserts.append(get_score(form=form, dag=dag))
                rec_query = f"select distinct redcap_record_id from redcap_record where redcap_form = '{form}' and redcap_data_access_group = '{dag}'"
                rec_list = self.redcap_db.query(session=self.db_session, query_text=rec_query, return_df=True)["redcap_record_id"].tolist()        
                for rec in rec_list:
                    score_inserts.append(get_score(form=form, dag=dag, rec=rec))
                                   
        score_df = pd.DataFrame(score_inserts)        
        self.redcap_db.insert_dataframe(self.db_session, 'quality_assessment_score', score_df)                            

        return None
    








    # def export_results(self):
        
    #     args = self.args
    #     log = self.log
        
    #     log.info(f'Exporting Data Quality Results')
        
    #     result_df = pd.DataFrame(self.result_list)
    #     result_df = result_df[['redcap_form','redcap_data_access_group','record_id','variable','check_type','check_name','check_dimension','check_value','check_passed','check_message']]

    #     # export excel file
    #     result_df.to_excel(os.path.join(args['output_path'], 'data_quality_results.xlsx'))  
        
    #     # export json file
    #     result_df.to_sql(os.path.join(args['output_path'], 'data_quality_results.db'), index=False, if_exists='replace')
        
    #     result_df.set_index(['redcap_form', 'redcap_data_access_group', 'record_id', 'variable', 'check_type'], inplace=True)
        
    #     def nest_dataframe(df):
    #         if df.index.nlevels == 1:
    #             return df.to_dict(orient='index')
    #         else:
    #             return df.groupby(level=0).apply(lambda df: nest_dataframe(df.droplevel(0))).to_dict()
       
    #     result_dict = nest_dataframe(result_df)
        
    #     with open(os.path.join(args['output_path'], 'data_quality_results.json'), 'w') as file:
    #         json.dump(result_dict, file, indent=4)
            
    #     #result_json = json.dumps(result_dict, indent=4)
        
    #     #result_df.to_json(os.path.join(args['output_path'], 'data_quality_results.json'), orient='table', indent=4)
    #     #result_dict = result_df.to_dict(orient='index')
        
    #     return None
    



    # def organize_dq_rules(self):
        
    #     def parse_code_list(code_string):

    #         codes = code_string.split(" | ")

    #         code_dict = {}

    #         for code in codes:
    #             elements = code.split("; ")
    #             code_dict[int(elements[0])] = elements[1]

    #         return code_dict

    #     args = self.args
    #     log = self.log

    #     log.info(f'Organizing Data Quality Rules')
        
    #     dd_path = args['data_dictionary_path']
    #     dq_path = args['data_quality_rules_path']
        
    #     uc_dd_dfs = []
    #     uc_dq_dfs = []
        
    #     dq_dict = {}

    #     uc_dict = {"UseCase1":"use_case_1", "UseCase3":"use_case_3", 
    #                "UseCase4&5":"use_case_4_and_5", "UseCase7":"use_case_7", 
    #                "UseCase6&8":"use_case_6_and_8"}
        
    #     for tab in uc_dict.keys():
    #         uc = uc_dict[tab]
    #         log.info(f'---- {uc}')

    #         dd_df = pd.read_excel(dd_path, sheet_name=tab)
    #         dd_df['uc'] = uc
    #         dd_df.rename(columns={'min':'range_min', 'max':'range_max'})
    #         uc_dd_dfs.append(dd_df)
            
    #         dq_df = pd.read_excel(dq_path, sheet_name=tab)
    #         dq_df['uc'] = uc
    #         dq_df.rename(columns={'min':'range_min', 'max':'range_max'})
    #         uc_dq_dfs.append(dq_df)

    #         dq_dict[uc] = {}
            
    #         for index, row in dq_df.iterrows():
    #             variable = row['variable']
    #             check_type = row['check_type']
                
    #             if variable not in dq_dict[uc]:
    #                 dq_dict[uc][variable] = {} 
    #             dq_dict[uc][variable][check_type] = {}
    #             dq_dict[uc][variable][check_type]['check_name'] = row['check']
    #             dq_dict[uc][variable][check_type]['check_dimension'] = row['check_dimension']
    #             dq_dict[uc][variable][check_type]['check_message'] = row['message']
                
    #             if check_type == 'datatype':
    #                 dq_dict[uc][variable][check_type]['check_datatype'] = row['datatype']
    #             if check_type in ['minimal_req','mandatory_req']:
    #                 dq_dict[uc][variable][check_type]['check_required'] = row['required']
    #                 dq_dict[uc][variable][check_type]['check_condition'] = row['req_condition']
    #             if check_type == 'range':
    #                 dq_dict[uc][variable][check_type]['check_min'] = row['min']
    #                 dq_dict[uc][variable][check_type]['check_max'] = row['max']
    #             if check_type == 'permissible':
    #                 code_dict = {}
    #                 if not pd.isnull(row['code_list']):
    #                     code_dict = parse_code_list(row['code_list'])
    #                 dq_dict[uc][variable][check_type]['check_values'] = code_dict

    #     dd_df = pd.concat(uc_dd_dfs)
    #     dq_df = pd.concat(uc_dq_dfs)
        
    #     self.redcap_db.insert_dataframe(self.db_session, 'data_dictionary', dd_df)
    #     self.redcap_db.insert_dataframe(self.db_session, 'quality_rules', dq_df)
        
    #     self.dq_dict = dq_dict
        
    #     return None





    # def retrieve_data_records(self):
        
    #     def export_records(redcap_form):

    #         data = {
    #             'token': self.args["redcap_tokens"][redcap_form],
    #             'content': 'record',
    #             'action': 'export',
    #             'format': 'json',
    #             'type': 'flat',
    #             'csvDelimiter': '',
    #             'rawOrLabel': 'raw',
    #             'rawOrLabelHeaders': 'raw',
    #             'exportCheckboxLabel': 'false',
    #             'exportSurveyFields': 'false',
    #             'exportDataAccessGroups': 'true',
    #             'returnFormat': 'json'
    #         }
    #         response = requests.post(self.args["redcap_server"],data=data)
    #         response_status = response.status_code
    #         response_json = response.json()
    
    #         return response_json

    #     args = self.args
    #     log = self.log

    #     log.info(f'Retrieving Data Records')

    #     record_list = []

    #     for redcap_form in args['redcap_forms']:

    #         log.info(f'---- {redcap_form}')

    #         # get list of records
    #         records = export_records(redcap_form)
    #         records = [{**d, "redcap_form": redcap_form} for d in records]
    #         record_list.extend(records)

    #     self.record_list = record_list

    #     return None

















    # def export_dags(self):
    
    #     data = {
    #         'token': self.args["redcap_token"],
    #         'content': 'dag',
    #         'format': 'json',
    #         'returnFormat': 'json'
    #     }
    #     response = requests.post(self.args["redcap_server"],data=data)
    #     response_status = response.status_code
    #     response_json = response.json()
    
    #     return response_json
    
    # def export_instruments(self):

    #     data = {
    #         'token': self.args["redcap_token"],
    #         'content': 'instrument',
    #         'format': 'json',
    #         'returnFormat': 'json'
    #     }
    #     response = requests.post(self.args["redcap_server"],data=data)
    #     response_status = response.status_code
    #     response_json = response.json()
    
    #     return response_json

    # def export_metadata(self):

    #     data = {
    #         'token': self.args["redcap_token"],
    #         'content': 'metadata',
    #         'format': 'json',
    #         'returnFormat': 'json'
    #     }
    #     response = requests.post(self.args["redcap_server"],data=data)
    #     response_status = response.status_code
    #     response_json = response.json()
    
    #     return response_json
    
    # def export_projects(self):

    #     data = {
    #         'token': self.args["redcap_token"],
    #         'content': 'project',
    #         'format': 'json',
    #         'returnFormat': 'json'
    #     }
    #     response = requests.post(self.args["redcap_server"],data=data)
    #     response_status = response.status_code
    #     response_json = response.json()
    
    #     return response_json
    

