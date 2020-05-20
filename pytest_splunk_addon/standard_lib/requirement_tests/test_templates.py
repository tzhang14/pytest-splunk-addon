
import logging
import pytest
import os
INTERVAL = 3
RETRIES = 3
import time

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
            self.logger.info("Issue parsing log file {}".format(filename))
            pytest.skip('Issue parsing log file')
        if model is None and escaped_event is not None:
            self.logger.info("No model present in file")
            pytest.skip('No model present in file')
        if sourcetype is None:
            self.logger.info("Issue finding sourcetype")
            assert result
        
        #ingest data
        indextime = int(time.time())
        search = f"|makeresults |eval _raw = \"{unescaped_event}\" |collect index=main sourcetype={sourcetype} source=pytest"
        ingest_search = splunk_search_util.checkQueryCountIsGreaterThanZero(
            search, interval=INTERVAL, retries=RETRIES
        )
        self.logger.info(f"Result of ingest search: {ingest_search}")
        #test data model
        search =f"| datamodel {model}  search | search source=pytest sourcetype={sourcetype} {escaped_event} |search  _indextime>={indextime}"
        result = splunk_search_util.checkQueryCountIsGreaterThanZero(
            search, interval=INTERVAL, retries=RETRIES
        )
        assert result, (
            f"No result found for the search.\nsearch={search}\n"
            f"interval={INTERVAL}, retries={RETRIES}"
        )