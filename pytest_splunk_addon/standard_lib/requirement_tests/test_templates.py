
import logging
import pytest
import os
INTERVAL = 3
RETRIES = 3

class ReqsTestTemplates(object):
    """
    Test templates to test the log files in the event_analytics folder 
    """
    logger = logging.getLogger()

    @pytest.mark.splunk_addon_searchtime
    def test_cim_params(self,splunk_searchtime_requirement_param,splunk_search_util):
        model = splunk_searchtime_requirement_param["model"]
        escaped_event = splunk_searchtime_requirement_param["escaped_event"]
        unescaped_event = splunk_searchtime_requirement_param["unescaped_event"]
        filename = splunk_searchtime_requirement_param["filename"]
        sourcetype = splunk_searchtime_requirement_param["sourcetype"]
        result = False
        if model is None and escaped_event is None:
            logging.info("Issue parsing log file")
            logging.info("Filename {}".format(filename))
            assert result
        if model is None and escaped_event is not None:
            logging.info("No model present in file")
            assert result
        if sourcetype is None:
            logging.info("Issue finding sourcetype")
            assert result
        
        #ingest data
        search = f"|makeresults |eval _raw = \"{unescaped_event}\" |collect index=main sourcetype={sourcetype} source=pytest"
        ingest_flag = splunk_search_util.checkQueryCountIsGreaterThanZero(
            search, interval=INTERVAL, retries=RETRIES
        )
        #test data model
        search =f"| datamodel {model}  search | search source=pytest sourcetype={sourcetype} {escaped_event}"
        result = splunk_search_util.checkQueryCountIsGreaterThanZero(
            search, interval=INTERVAL, retries=RETRIES
        )
        assert result