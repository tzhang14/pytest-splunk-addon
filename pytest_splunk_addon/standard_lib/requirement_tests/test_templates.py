
import logging
import pytest
import os
INTERVAL = 0
RETRIES = 0

class ReqsTestTemplates(object):
    logger = logging.getLogger()
    @pytest.mark.splunk_addon_searchtime
    def test_cim_params(self,splunk_searchtime_requirement_param,splunk_search_util):
        model = splunk_searchtime_requirement_param["model"]
        event = splunk_searchtime_requirement_param["event"]
        search =f"| datamodel {model}  search | search  {event}"
        result = splunk_search_util.checkQueryCountIsGreaterThanZero(
            search, interval=INTERVAL, retries=RETRIES
        )
        assert result
