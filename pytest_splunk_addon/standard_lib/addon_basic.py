# -*- coding: utf-8 -*-
"""
Base class for test cases. Provides test cases to verify
field extractions and CIM compatibility.
"""
import logging
import pytest

from .fields_tests import FieldTestTemplates
from .cim_tests import CIMTestTemplates
INTERVAL = 3
RETRIES = 3

class Basic():
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
    def test_requirement(self,splunk_search_util,get_model_name,get_event,caplog):
        """
        Test case to pick requirements.txt
        This test case checks props stanza is not empty, blank and dash value.
        Args:
        """
        # f = open(get_requirements_file, "r")
        # contents =f.read()
        # self.logger.debug(contents)
        # caplog.set_level(logging.DEBUG)
        # self.logger.info(f" modelname {get_model_name}")
        # self.logger.debug(f" event {get_event}")
        for model in get_model_name:
            self.logger.info(f" modelname {model}")
            search =f"| datamodel {model}  search | search sourcetype=cisco:asa {get_event}"
            result = splunk_search_util.checkQueryCountIsGreaterThanZero(
                search, interval=INTERVAL, retries=RETRIES
            )
        # search =f"| datamodel {model}  search | search sourcetype=cisco:asa {get_event}"
        # result = splunk_search_util.checkQueryCountIsGreaterThanZero(
        #     search, interval=INTERVAL, retries=RETRIES
           
        # )
        assert result

    pass
