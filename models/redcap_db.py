# -*- coding: utf-8 -*-
# ! /usr/bin/env python

#https://docs.sqlalchemy.org/en/14/orm/quickstart.html
#https://docs.sqlalchemy.org/en/14/core/type_basics.html#sql-standard-and-multiple-vendor-types
#https://www.sqlshack.com/introduction-to-sqlalchemy-in-pandas-dataframe/
#https://www.tutorialspoint.com/sqlalchemy/sqlalchemy_introduction.htm#

from sqlalchemy import MetaData, Table, Column, ForeignKey, Index
from sqlalchemy import select, insert, update, delete, text
from sqlalchemy import TEXT, NUMERIC, INTEGER, REAL, BOOLEAN, DATETIME, DATE, TIME, JSON, BLOB

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

import pandas as pd
from datetime import datetime

Base = declarative_base()

class redcap_db(object):

    # Initialize
    def __init__(self, db_connect_string):

        self.engine = create_engine(db_connect_string, echo=False)
        self.session_maker = sessionmaker(bind = self.engine)

        return None

    # Exit
    def __exit__(self):

        self.Session.close()
        self.engine.close()

        return None

    # Create Database
    def create_database(self, check):

        Base.metadata.create_all(self.engine, checkfirst=check)

        return None
    
    # Drop Database
    def drop_database(self, check):

        Base.metadata.drop_all(self.engine, checkfirst=check)

        return None

    # Clear Database
    def clear_database(self, check):

        #Base.metadata.drop_all(self.engine, checkfirst=check)
        metadata = MetaData(bind=self.engine)
        metadata.reflect()
        
        with self.get_session() as session:
            for table in metadata.sorted_tables:
                try:
                    session.execute(table.delete())
                except:
                    session.rollback()
                    raise
                else:
                    session.commit()

        return None

    # Drop Table
    def drop_table(self, table):
        rem_table = Table(table, Base.metadata)
        rem_table.drop(self.engine, checkfirst=True)
        return None

    # Clear Table
    def clear_table(self, table):
        clear_table = Table(table, Base.metadata)
        with self.get_session() as session:
            try:
                session.query(clear_table).delete()
            except:
                session.rollback()
                raise
            else:
                session.commit()

        return None

    # Create Session
    def get_session(self):

        return self.session_maker()

    # Query
    def query(self, session=None, table=None, query_text=None, return_df=False):
        if return_df:
            #query = session.query(text(query_text))
            result_df = pd.read_sql(query_text, session.bind)
            return result_df
        else:
            if session:
                if not query_text == None:
                    result = session.query(table).from_statement(text(query_text)).all()
                else:
                    result = session.query(table).all()
                return result


    # Insert Dataframe
    def insert_dataframe(self, session, table_name, data_df):

        data_dict = data_df.to_dict(orient='records')
        metadata = MetaData(bind=self.engine)
        metadata.reflect()
        table = Table(table_name, metadata, autoload_with=self.engine)

        try:
            session.execute(table.insert(), data_dict)
        except:
            session.rollback()
            raise
        else:
            session.commit()

        return None
    
    def insert_dicts(self, session, table_name, data_dict):
        """
        Inserts a list of dictionaries into the specified table.

        Parameters:
        session (Session): SQLAlchemy session object.
        table_name (str): Name of the table to insert data into.
        data_dict (dict or list of dict): A list of dictionaries, where each dictionary represents a row.

        Returns:
        None
        """
        
        data_dicts = None
        if isinstance(data_dict, dict):
            data_dicts = [data_dict]
        elif isinstance(data_dict, list):
            data_dicts = data_dict

        # Load the metadata and reflect to get table details
        metadata = MetaData(bind=self.engine)
        metadata.reflect()
        table = Table(table_name, metadata, autoload=True)

        try:
            # Insert data
            session.execute(table.insert(), data_dicts)
        except Exception as e:
            session.rollback()
            raise e
        else:
            session.commit()

        return None


    # Insert List
    def insert_list(self, session, insert_list):

        try:
            session.add_all(insert_list)
        except:
            session.rollback()
            raise
        else:
            session.commit()

        return None

# -------------------
# Redcap Quality Results
# -------------------
class RedcapRecord(Base):
    __tablename__ = 'redcap_record'

    rec_id = Column(INTEGER, primary_key=True, autoincrement=True)
    redcap_form = Column(TEXT)
    redcap_data_access_group = Column(TEXT)
    redcap_record_id = Column(TEXT)
    redcap_data = Column(TEXT)
    
class DataDictionary(Base):
    __tablename__ = 'data_dictionary'
    
    dd_id = Column(INTEGER, primary_key=True, autoincrement=True)
    uc = Column(TEXT)
    variable = Column(TEXT)
    matrix = Column(TEXT)
    matrix_parent = Column(INTEGER)
    matrix_start = Column(INTEGER)
    matrix_end = Column(INTEGER)
    required = Column(TEXT)
    req_condition = Column(TEXT)
    minimal = Column(TEXT)
    mandatory = Column(TEXT)
    group = Column(TEXT)
    display_type = Column(TEXT)
    display_label = Column(TEXT)
    code_list = Column(TEXT)
    code_default = Column(INTEGER)
    output_type = Column(TEXT)
    min = Column(INTEGER)
    max = Column(INTEGER)
    note = Column(TEXT)
    branching = Column(TEXT)

class QualityRule(Base):
    __tablename__ = 'quality_rule'
    
    qr_id = Column(INTEGER, primary_key=True, autoincrement=True)
    uc = Column(TEXT)
    variable = Column(TEXT)
    check = Column(TEXT)
    check_dimension = Column(TEXT)
    check_type = Column(TEXT)
    check_string = Column(TEXT)
    datatype = Column(TEXT)
    required = Column(TEXT)
    req_condition = Column(TEXT)
    min = Column(INTEGER)
    max = Column(INTEGER)
    code_list = Column(TEXT)
    message = Column(TEXT)

class QualityRuleWeight(Base):
    __tablename__ = 'quality_rule_weight'

    qrw_id = Column(INTEGER, primary_key=True, autoincrement=True)
    check_type = Column(TEXT)
    weight = Column(REAL)

class QualityAssessment(Base):
    __tablename__ = 'quality_assessment'

    qa_id = Column(INTEGER, primary_key=True, autoincrement=True)
    redcap_form = Column(TEXT)
    redcap_data_access_group = Column(TEXT)
    redcap_record_id = Column(TEXT)
    variable = Column(TEXT)
    check_dimension = Column(TEXT)
    check_type = Column(TEXT)
    check_name = Column(TEXT)
    check_value = Column(TEXT)
    check_passed = Column(BOOLEAN)
    check_message = Column(TEXT)

class QualityAssessmentCount(Base):
    __tablename__ = 'quality_assessment_count'

    qac_id = Column(INTEGER, primary_key=True, autoincrement=True)
    redcap_form = Column(TEXT)
    redcap_data_access_group = Column(TEXT)
    redcap_record_id = Column(TEXT)
    check_dimension = Column(TEXT)
    check_type = Column(TEXT)
    total_checks = Column(INTEGER)
    passed_checks = Column(INTEGER)
    
class QualityAssessmentResult(Base):
    __tablename__ = 'quality_assessment_result'

    qar_id = Column(INTEGER, primary_key=True, autoincrement=True)
    result_level = Column(TEXT) # dag, dag_form, dag_form_record, dag_form_record_variable, form, record, variable
    redcap_form = Column(TEXT)
    redcap_data_access_group = Column(TEXT)
    redcap_record_id = Column(TEXT)
    variable = Column(TEXT)    
    completeness_score = Column(REAL)
    conformance_score = Column(REAL)
    plausibility_score = Column(REAL)
    min_req_score = Column(REAL)
    man_req_score = Column(REAL)
    permissible_score = Column(REAL)
    datatype_score = Column(REAL)
    datatype_score = Column(REAL)
    total_score = Column(REAL)
    results_json = Column(TEXT)
