
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
        escaped_event = splunk_searchtime_requirement_param["escaped_event"]
        unescaped_event = splunk_searchtime_requirement_param["unescaped_event"]
        filename = splunk_searchtime_requirement_param["filename"]
        sourcetype = splunk_searchtime_requirement_param["sourcetype"]

        if ((model == None) or (escaped_event == None)):
            logging.info("Issue parsing log file")
            logging.info("Filename {}".format(filename))
            assert False
        
        #adding to ingest data
        search = f"|makeresults |eval _raw = \"{unescaped_event}\" |collect index=main sourcetype={sourcetype} source=test1234"
        result1 = splunk_search_util.checkQueryCountIsGreaterThanZero(
            search, interval=INTERVAL, retries=RETRIES
        )
        #to check the datamodel
        search =f"| datamodel {model}  search | search  {escaped_event}"
        result = splunk_search_util.checkQueryCountIsGreaterThanZero(
            search, interval=INTERVAL, retries=RETRIES
        )
        assert result
    # @pytest.mark.splunk_addon_searchtime
    # def test_ingest(self,splunk_search_util,splunk_searchtime_requirement_file):
    #     search = "|makeresults |eval _raw = \"May 10 07:15:20 dummy.dvc %ASA-2-106001:Inbound TCP connection denied from 10.0.0.1/1111 to 10.0.0.2/2222 flags dummy_tcp_flags on interface dummy_interface_name\" |collect index=main sourcetype=cisco:asa source=test1234"
    #     result = splunk_search_util.checkQueryCountIsGreaterThanZero(
    #         search, interval=INTERVAL, retries=RETRIES
    #     )
    #     search = "| datamodel Network_Traffic search | search May 10 07:15:20 dummy.dvc %ASA-2-106001: Inbound TCP connection denied from 10.0.0.1/1111 to 10.0.0.2/2222 flags dummy_tcp_flags on interface dummy_interface_name"
    #     result = splunk_search_util.checkQueryCountIsGreaterThanZero(
    #         search, interval=INTERVAL, retries=RETRIES
    #     )
    #     assert result