"""
Generates test cases to verify the event analytics logs. 
"""
import pytest
import json
import logging
import os
import configparser
from xml.etree import cElementTree as ET
import re


LOGGER = logging.getLogger("pytest-splunk-addon")
class SrcRegex(object):
    def __init__(self):
        self.regex_src = None
        self.source_type = None

class ReqsTestGenerator(object):
    """
    Generates test cases to test the events in the log files of the event anlytics folder
    * Provides the pytest parameters to the test_templates.py.   
    Args:
        app_path (str): Path of the app package
    """
    def __init__(self, app_path):
        logging.info("initializing ReqsTestGenerator class")
        self.package_path = app_path
        #self.folder_path = os.path.join(str(self.package_path), "event_analytics")

    def generate_tests(self, fixture):
        """
        Generate the test cases based on the fixture provided 
        Args:
            fixture(str): fixture name
        """
        if fixture.endswith("file"):
            yield from self.generate_cim_req_files()
        elif fixture.endswith("param"):
            yield from self.generate_cim_req_params()
        
    def generate_cim_req_files(self):
        file_list = []
        self.extractRegexTransforms()
        folder_path = os.path.join(str(self.package_path), "event_analytics")
        if os.path.isdir(folder_path):
            for file1 in os.listdir(folder_path):
                filename = os.path.join(folder_path, file1)
                if filename.endswith(".log"):
                    file_list.append(filename)
                    yield pytest.param(filename,
                    id=str(filename))

    def generate_cim_req_params(self):
        """
        Generate & Yield pytest.param for each test case.
        Params = Model_name with respective Event  
        """
        req_test_id = 0
        src_regex =[]
        src_regex = self.extractRegexTransforms()
        folder_path = os.path.join(str(self.package_path), "event_analytics")
        if os.path.isdir(folder_path):
            for file1 in os.listdir(folder_path):
                filename = os.path.join(folder_path, file1)
                if filename.endswith(".log"):
                    try:
                        model = None
                        escaped_event = None
                        unescaped_event = None
                        sourcetype = None
                        abc = self.check_xml_format(filename)
                        root = self.get_root(filename)
                        for event_tag in root.iter('event'):
                            unescaped_event = self.get_event(event_tag)
                            sourcetype = self.extractSourcetype(src_regex, unescaped_event)
                            escaped_event = self.escape_char_event(unescaped_event)  
                            model_list = self.get_models(event_tag)
                            if(len(model_list) == 0):
                                raise Exception
                            for model in model_list:
                                model = model.replace(" ", "_")
                                req_test_id = req_test_id + 1
                                yield pytest.param(
                                {
                                        "model": model,
                                        "escaped_event": escaped_event,
                                        "unescaped_event": unescaped_event,
                                        "filename":filename,
                                        "sourcetype":sourcetype,
                                },
                                    id=f"{model}::{filename}::req_test_id::{req_test_id}",
                                )
                    except Exception:
                        logging.info("--check xml true or not {}".format(abc))
                        req_test_id = req_test_id + 1
                        yield pytest.param(
                        {
                            "model": model,
                            "escaped_event": escaped_event,
                            "unescaped_event": unescaped_event,
                            "filename":filename,
                            "sourcetype":sourcetype,
                        },
                            id=f"{model}::{filename}::req_test_id::{req_test_id}",
                        )

    def get_models(self,root):
        """
        Input: Root of the xml file
        Function to return list of models in each event of the log file
        """
        model_list=[]
        for model in root.iter('model'):
            model_list.append(str(model.text))
        return model_list

    def get_event(self,root):
        """
        Input: Root of the xml file
        Function to return raw event string
        """
        event = None
        for raw in root.iter('raw'):
            event = raw.text
        return event

    def get_root(self,filename):
        """
        Input: Filename ending with .log extension
        Function to return raw event string
        """
        tree = ET.parse(filename)
        root = tree.getroot()
        return root

    def check_xml_format(self,file_name):
        if(ET.parse(file_name)):
            return True
    
    def escape_char_event(self,event):
        """
        Input: Event getting parsed
        Function to escape special characters in Splunk 
        https://docs.splunk.com/Documentation/StyleGuide/current/StyleGuide/Specialcharacters
        """
        escape_splunk_chars = ["\\","`", "~", "!","@", "#","$", "%", 
        "^","&","*","(",")","-","=","+","[","]","}","{","|",
        ";",":","'","\"","\,","<",">","\/","?"]
        for character in escape_splunk_chars:
            event = event.replace(character,'\\'+ character)
        return event

    def extractRegexTransforms(self):
        """
        Requirement : app transform.conf
        Return: SrcRegex objects list containing pair of regex and sourcetype 
        """
        parser = configparser.ConfigParser(interpolation=None)
        transforms_path = os.path.join(str(self.package_path), "default/transforms.conf")
        parser.read_file(open(transforms_path))
        list_src_regex = []
        for stanza in parser.sections():
            stanza_keys=list(parser[stanza].keys())
            obj = SrcRegex()
            if ("dest_key" in stanza_keys):
                if (str(parser[stanza]["dest_key"]) == "MetaData:Sourcetype"):
                    for key in stanza_keys:
                        key_value = str(parser[stanza][key])
                        if (key == "regex"):
                            obj.regex_src = key_value
                        if (key == "format"):
                            obj.source_type = key_value
                    list_src_regex.append(obj)            
        return list_src_regex

    def extractSourcetype(self,list_src_regex,event):
        """
        Input: event, List of SrcRegex
        Return:Sourcetype of the event
        """
        sourcetype = None
        for regex_src_obj in list_src_regex:
            regex_match = re.search(regex_src_obj.regex_src, event)
            if(regex_match):
                _,sourcetype = str(regex_src_obj.source_type).split('::',1)
        return sourcetype
