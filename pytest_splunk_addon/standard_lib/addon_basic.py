# -*- coding: utf-8 -*-
"""
Base class for test cases. Provides test cases to verify
field extractions and CIM compatibility.
"""
import logging
import pytest

from .fields_tests import FieldTestTemplates
from .cim_tests import CIMTestTemplates
from .requirement_tests import ReqsTestTemplates


class DataNode(object):
    def __init__(self):
        self.event = None
        self.models = None

#class Basic(ReqsTestTemplates,FieldTestTemplates,CIMTestTemplates):
class Basic(ReqsTestTemplates):
    """
    Base class for test cases. Inherit this class to include the test 
        cases for an Add-on.
    """
    @pytest.mark.splunk_addon_searchtime
    def test_connection_splunk(self,splunk_search_util):
        search = "search (index=_audit) daysago=60| head 5"

            # run search
        result = splunk_search_util.checkQueryCountIsGreaterThanZero(
            search,
            interval=1, retries=1)
        assert result