
import logging
import pytest
from xml.etree import cElementTree as ET
import os

INTERVAL = 0
RETRIES = 0
class ReqsTestTemplates(object):
    logger = logging.getLogger()
    @pytest.mark.splunk_addon_searchtime
    def test_cim_requirements(self,splunk_search_util,splunk_searchtime_requirement_cim,caplog):
        """
        Test case to pick requirements.txt
        Args:
        """
        list_nodes = []
        file_name = splunk_searchtime_requirement_cim
        root = self.get_root(file_name)
        result = []
        for event_tag in root.iter('event'):
            event = self.get_event(event_tag)
            model_list = self.get_models(event_tag)
            for model in model_list:
                model = model.replace(" ", "_")
                search =f"| datamodel {model}  search | search  {event}"
                result = splunk_search_util.checkQueryCountIsGreaterThanZero(
                    search, interval=INTERVAL, retries=RETRIES
                )
                self.logger.info(f"Model Name {model}")
                self.logger.info(f"Event in quest {event}")
        assert result
        for obj in list_nodes:
            self.logger.info(obj.__dict__)
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