import pytest
import json
import logging
import os


LOGGER = logging.getLogger("pytest-splunk-addon")
class ReqsTestGenerator(object):
    """
    Generates test cases to test the knowledge objects of an Add-on.
    * Provides the pytest parameters to the test templates.
    * Supports field_bank: List of fields with patterns and expected
        values which should be tested for the Add-on.
    
    Args:
        app_path (str): Path of the app package
    """

    def __init__(self, app_path):
        logging.info("initializing ReqsTestGenerator class")
        self.package_path = app_path


    def generate_tests(self, fixture):
        """
        Generate the test cases based on the fixture provided 
        supported fixtures:
        Args:
            fixture(str): fixture name

        """
        if fixture.endswith("cim"):
            yield from self.generate_cim_req_files()
        
    def generate_cim_req_files(self):
        folder_path = os.path.join(str(self.package_path), "event_analytics")
        file_list = []
        for file1 in os.listdir(folder_path):
            filename = os.path.join(folder_path, file1)
            logging.info("---Filename {}".format(filename))
            if filename.endswith(".log"):
                file_list.append(filename)
                yield pytest.param(filename,
                id=str(filename))
