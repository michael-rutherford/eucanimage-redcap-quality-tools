import os
import sys
import json
from datetime import datetime
import multiprocessing

from modules.quality_tools import quality_tools
from modules.redcap_tools import redcap_tools
from modules.log_helper import log_helper

def run_quality_checks(args, log):
    
    #log.info(f'Running Quality Checks')
    
    tools = redcap_tools(args, log)
    tools.refresh(args['refresh_all'])    

    tools.run_quality_checks()
    tools.get_quality_counts()
    #tools.get_quality_results()
    # tools.export_results()
  
    return None


def main(argv):

    # --------------------------------------
    # parse arguments
    # --------------------------------------
    
    args = {}

    # if no arguments, use default values for dev testing
    if len(argv) == 0:
        args['config_path'] = r"D:\redcap\config\config.json"
    else:
        args['config_path'] = argv[0]
        
    # --------------------------------------
    # parse config file
    # --------------------------------------

    with open(args['config_path']) as json_file:
        json_data = json.load(json_file)
        
        args['redcap_server'] = json_data['redcap_server']
        args['redcap_forms'] = json_data['redcap_forms']
        args['redcap_tokens'] = json_data['redcap_tokens']
        args['redcap_dags'] = json_data['redcap_dags']
        args['rule_weights'] = json_data['rule_weights']
        args['data_dictionary_path'] = json_data['data_dictionary_path']
        args['data_quality_rules_path'] = json_data['data_quality_rules_path']
        args['output_path'] = json_data['output_path']
        args['log_path'] = json_data['log_path'] 
        args['log_level'] = json_data['log_level'] if 'log_level' in json_data else "info"
        args['refresh_all'] = json_data['refresh_all'] if 'refresh_all' in json_data else True

    # --------------------------------------
    # initialize logging
    # --------------------------------------
    start_time = datetime.now()
    prog_name = "eucanimage-redcap-quality-tools"
    log = log_helper(start_time, prog_name, args['log_path'], args['log_level'])
    # --------------------------------------

    log.info(f'Executing {prog_name}')

    run_quality_checks(args, log)

    #------------------------------------------
    # calculate duration
    #------------------------------------------
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    seconds_in_day = 24 * 60 * 60
    duration = divmod(elapsed_time.days * seconds_in_day + elapsed_time.seconds, 60)

    log.info(f'Complete - Duration: {duration}')

    
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", True)
    main(sys.argv[1:])

