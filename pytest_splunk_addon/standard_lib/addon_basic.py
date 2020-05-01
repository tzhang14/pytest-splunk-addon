# -*- coding: utf-8 -*-
"""
Base class for test cases. Provides test cases to verify
field extractions and CIM compatibility.
"""
import logging
import pytest

from .fields_tests import FieldTestTemplates
from .cim_tests import CIMTestTemplates
from xml.etree import cElementTree as ET
INTERVAL = 1
RETRIES = 0

class Basic(object):
    """
    Base class for test cases. Inherit this class to include the test 
        cases for an Add-on.
    """
    logger = logging.getLogger() 
    @pytest.mark.splunk_addon_searchtime
    def test_connection_splunk(self,splunk_search_util):
        search = "search (index=_audit) daysago=60| head 5"

            # run search
        result = splunk_search_util.checkQueryCountIsGreaterThanZero(
            search,
            interval=1, retries=1)
        assert result

    @pytest.mark.splunk_addon_searchtime
    def test_requirement(self,splunk_search_util,fetch_cimreq_location,caplog):
        """
        Test case to pick requirements.txt
        This test case checks props stanza is not empty, blank and dash value.
        Args:
        """
        for file_name in fetch_cimreq_location:
            root = self.get_root(file_name)
            result = []
            for event_tag in root.iter('event'):
                event = self.get_event(event_tag)
                model_list = self.get_models(event_tag)
                for models in model_list:
                    models = models.replace(" ", "_")
                    search =f"| datamodel {models}  search | search  {event}"
                    result.append(splunk_search_util.checkQueryCountIsGreaterThanZero(
                        search, interval=INTERVAL, retries=RETRIES
                    ))
                    self.logger.info(f" file {file_name}")
                    self.logger.info(f" modelname {models}")
                    self.logger.info(f" Event {event}")
                    self.logger.info(f" Search Result {result}")
            assert result

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
