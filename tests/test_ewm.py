#!/usr/bin/env python3
"""
    Unit tests for ewm.Ewm class.
    To run a single test: ./test_ewm.py TestEwm.test_whoami
"""
import json
import os
import sys
import tempfile
import time
import unittest

REPO_PATH = os.path.dirname(os.path.abspath(__file__))
REPO_PATH = REPO_PATH.replace("tests", "")
sys.path.append(REPO_PATH)
import ewm

# https://jazz07.rchland.ibm.com:13443/jazz/web/projects/Cognitive%20Systems%20Software%20Development#action=com.ibm.team.workitem.viewWorkItem&id=282739
TEST_WORK_ITEM = "282739"


class TestEwm(unittest.TestCase):

    @unittest.skip("TODO")
    def test_create(self):
        pass

    def test_modify(self):
        """ Test multiple attributes """

        current_time = time.strftime("%B %d, %Y %H:%M:%S", time.localtime())

        instance = ewm.Ewm()
        expected = {"Description": current_time,
                    "Tags": "foo, bar",
                    "System Name": "Denali"
                    }

        attributes = ["Description:", current_time,
                      ",", "Tags:", "foo bar",
                      ",", "System Name:", "Denali"]

        data = instance.modify(id=TEST_WORK_ITEM, attributes=attributes)

        actual = {"Description": data["Description"],
                  "Tags": data["Tags"],
                  "System Name": data["System Name"]
                  }
        self.assertEqual(expected, actual)

    def test_modify2(self):
        """ Test modify from JSON File """

        json_data = {"Severity Justification": "test_modify2",
                     "Priority Justification": "this is low priority",
                     "Severity": "3 - Moderate",
                     "Description": "running test_modify2",
                     "System Name": "new name",
                     }

        expected = json_data

        temp_FH = tempfile.NamedTemporaryFile(mode="w", delete=False)

        json.dump(json_data, temp_FH)
        temp_FH.close()

        instance = ewm.Ewm()

        data = instance.modify(id=TEST_WORK_ITEM, wifile=temp_FH.name)

        actual = {"Severity Justification": data["Severity Justification"],
                  "Priority Justification": data["Priority Justification"],
                  "Severity": data["Severity"],
                  "Description": data["Description"],
                  "System Name": data["System Name"]
                  }

        os.remove(temp_FH.name)

        self.assertEqual(expected, actual)

    @unittest.skip("TODO")
    def test_addnote(self):
        pass

    def test_view(self):

        instance = ewm.Ewm()

        data = instance.view(TEST_WORK_ITEM)
        actual = data["Summary"]

        expected = "test - feature type"
        self.assertEqual(expected, actual)

    def test_help(self):
        """ Test top help and a subcommand help """

        instance = ewm.Ewm()
        found_it = False
        output = instance.help()
        expected = "Available Subcommands:"
        for line in output:
            if expected in line:
                found_it = True
                break

        if not found_it:
            self.fail("Couldn't list top help message: {}".format(output))

        found_it = False
        output = instance.help("whoami")
        expected = "Help for: whoami"

        for line in output:
            if expected in line:
                found_it = True
                break

        self.assertTrue(found_it, "Couldn't list whoami help {}".format(output))

    def test_display(self):
        instance = ewm.Ewm()

        data = instance.display(TEST_WORK_ITEM)
        actual = data["Filed Against"]

        expected = "fips_build"
        self.assertEqual(expected, actual)

    def test_whoami(self):
        instance = ewm.Ewm()

        expected = "ibm.com"

        whoami = instance.whoami()

        actual = whoami.endswith(expected)

        self.assertTrue(actual, whoami)

    def test_setcwe(self):
        """ test both CLEAR and setcwe subcommands """
        instance = ewm.Ewm()

        expected = {"Repository": "https://jazz07.rchland.ibm.com:13443/jazz",
                    "Project": "CSSD"}

        actual = {"Repository": "",
                  "Project": ""}

        instance.CLEAR()
        data = instance.setcwe()

        for line in data:
            line = line.strip()
            if "Repository" in line:
                line = line.replace("Repository: ", "")
                actual["Repository"] = line
            elif "Project" in line:
                line = line.replace("Project: ", "")
                actual["Project"] = line

        # Make sure this testcase data is deleted at the end.
        instance.CLEAR()
        self.assertEqual(expected, actual)

    def test_listqueries(self):

        instance = ewm.Ewm()

        expected = "Active STG Defects I Am Subscribed To"
        data = instance.listqueries()
        found_it = False
        for query in data:
            name = query["Name"]
            if name == expected:
                found_it = True
                break

        self.assertTrue(found_it, "Couldn't find a query matching: {}".format(expected))

    def test_runquery(self):
        instance = ewm.Ewm()

        query_name = "Active STG Defects I Am Subscribed To"
        data = instance.runquery(query_name)

        self.assertTrue(len(data["results"]) > 0, data)

    def test_subscribe(self):
        """ Test both subscribe and unsubscribe """

        instance = ewm.Ewm()
        whoami = instance.whoami()
        whoami_list = [whoami]

        # Do an initial unsubscribe in case the id is already in there.  An error
        # gets thrown if you try to subscribe an already existing ID.
        unsubscribed_list = instance.unsubscribe(TEST_WORK_ITEM, whoami)

        subscribed_list = instance.subscribe(TEST_WORK_ITEM, whoami_list)
        if whoami not in subscribed_list:
            self.fail(subscribed_list)

        unsubscribed_list = instance.unsubscribe(TEST_WORK_ITEM, whoami)
        if whoami in unsubscribed_list:
            self.fail(unsubscribed_list)

    def test_link(self):
        """ Test both link and unlink """
        instance = ewm.Ewm()
        link_type = "Related Artifacts"
        google = "http://www.google.com"
        urls = [google]

        # Initially remove if it exists from previous run
        instance.unlink(TEST_WORK_ITEM, link_type, urls)

        instance.link(TEST_WORK_ITEM, link_type, urls)
        data = instance.view(TEST_WORK_ITEM)

        found_it = False
        for item in data[link_type]:
            if google in item["url"]:
                found_it = True
                break

        if not found_it:
            msg = "Couldn't find url in work item: {}\n".format(TEST_WORK_ITEM)
            msg += json.dumps(data[link_type], indent=4, sort_keys=True)
            self.fail(msg)

        found_it = False
        instance.unlink(TEST_WORK_ITEM, link_type, urls)
        data = instance.view(TEST_WORK_ITEM)
        for item in data[link_type]:
            if google in item["url"]:
                msg = "Couldn't remove link {} in work item: {}\n".format(TEST_WORK_ITEM,
                                                                          google)
                msg += json.dumps(data[link_type], indent=4, sort_keys=True)
                self.fail(msg)

        return

    @unittest.skip("TODO")
    def test_addcomment(self):
        pass

    def test_list(self):
        instance = ewm.Ewm()

        # Run test with qualifier
        topic = "attributes"
        qualifier = "STG Defect"
        found_it = False

        output = instance.list(topic, qualifier)
        expected = "Related Artifacts"
        for line in output:
            line = line.strip()
            if expected in line:
                found_it = True
                break

        if not found_it:
            self.fail("Couldn't find list {} for {}\n{}".format(topic,
                                                                qualifier,
                                                                output))

        # Run test without qualifier
        found_it = False
        topic = "cwe"
        qualifier = ""

        output = instance.list(topic)
        expected = "Repository: "
        for line in output:
            line = line.strip()
            if expected in line:
                found_it = True
                break

        if not found_it:
            self.fail("Couldn't list topic {}\n{}".format(topic, output))

        return

    def test_search(self):
        instance = ewm.Ewm()
        search_text = "Code Update Signing from Signing Server"
        max_num = 2

        data = instance.search(search_text, max_num)

        if len(data["results"]) > max_num:
            msg = "Search returned results over max number: {}\n".format(max_num) + \
                  json.dumps(data, indent=4, sort_keys=True)
            self.fail(msg)

        if len(data["results"]) == 0:
            self.skipTest("The search didn't return any results: {}".format(search_text))

        expected = "Code Update Signing from Signing Server"
        actual = ""

        for result in data["results"]:
            if (result["Id"] == "276281"):
                actual = result["Summary"]

        self.assertEqual(expected, actual, json.dumps(data, indent=4, sort_keys=True))

    @unittest.skip("TODO")
    def test_swat_catowners(self):
        pass


if (__name__ == "__main__"):
    unittest.main(verbosity=2)
