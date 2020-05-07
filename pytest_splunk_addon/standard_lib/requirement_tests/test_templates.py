
import logging
import pytest
import os
INTERVAL = 0
RETRIES = 0

class ReqsTestTemplates(object):
    """
    Test templates to test the log files in the event_analytics folder 
    """
    logger = logging.getLogger()

    @pytest.mark.splunk_addon_searchtime
    def test_cim_params(self,splunk_searchtime_requirement_param,splunk_search_util):

        #to do check if xml file has bad format
        model = splunk_searchtime_requirement_param["model"]
        event = splunk_searchtime_requirement_param["event"]
        filename = splunk_searchtime_requirement_param["filename"]

        if ((model == None) or (event == None)):
            logging.info("Issue parsing log file")
            logging.info("Filename {}".format(filename))
            assert False
        search =f"| datamodel {model}  search | search  {event}"
        result = splunk_search_util.checkQueryCountIsGreaterThanZero(
            search, interval=INTERVAL, retries=RETRIES
        )
        assert result
