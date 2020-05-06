import pytest
import json
import logging
import os
from xml.etree import cElementTree as ET

LOGGER = logging.getLogger("pytest-splunk-addon")

class ReqsTestGenerator(object):
    """
    Generates test cases to test the knowledge objects of an Add-on.
    * Provides the pytest parameters to the test templates.
    * Supports field_bank: List of fields with patterns and expected
        values which should be tested for the Add-on.
    
    Args:
        app_path (str): Path of the app package
    """

    def __init__(self, app_path):
        logging.info("initializing ReqsTestGenerator class")
        self.package_path = app_path
        self.folder_path = os.path.join(str(self.package_path), "event_analytics")

    def generate_tests(self, fixture):
        """
        Generate the test cases based on the fixture provided 
        supported fixtures:
        Args:
            fixture(str): fixture name

        """
        if fixture.endswith("cim"):
            yield from self.generate_cim_req_files()
        elif fixture.endswith("param"):
            yield from self.generate_cim_req_params()
        
    def generate_cim_req_files(self):
        file_list = []
        #self.generate_cim_req_params()
        for file1 in os.listdir(self.folder_path):
            filename = os.path.join(self.folder_path, file1)
            logging.info("---Filename {}".format(filename))
            if filename.endswith(".log"):
                file_list.append(filename)
                yield pytest.param(filename,
                id=str(filename))

    def generate_cim_req_params(self):
        for file1 in os.listdir(self.folder_path):
            filename = os.path.join(self.folder_path, file1)
            logging.info("--generate cim params-Filename {}".format(filename))
            if filename.endswith(".log"):
                root = self.get_root(filename)
                event_no = 0
                for event_tag in root.iter('event'):
                    event = self.get_event(event_tag)
                    event = self.escape_char_event(event)
                    logging.info("{}".format(event))   
                    model_list = self.get_models(event_tag)
                    for model in model_list:
                        model = model.replace(" ", "_")
                        event_no = event_no + 1
                        yield pytest.param(
                        {
                                "model": model,
                                "event": event,
                        },
                            id=f"{model}::{filename}::Event_No::{event_no}",
                        )             

    def get_models(self,root):
        model_list=[]
        for model in root.iter('model'):
            model_list.append(str(model.text))
        return model_list

    def get_event(self,root):
        event = None
        for raw in root.iter('raw'):
            event = raw.text
        return event

    def get_root(self,filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        return root

    def yield_test(self):
        for x in range(3, 6):
            yield(x)

    def escape_char_event(self,event):
       event = event.replace("\\", "\\\\")
       event = event.replace("=", "\=")
       return event
    #    escape_splunk_chars = ["`", "~", "!","@", "#","$", "%", 
    #    "%", "^","&","*","(",")","-","+","|","[","]","}","{","|",
    #    ";",":","'","<",">","?"]
    #    for character in escape_splunk_chars:
    #         event = event.replace(character,"\\"+ character)