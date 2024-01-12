import configparser
import json
import time

import mpp_data
import sys
from pyopenproject.openproject import OpenProject
from pyopenproject.model.project import Project
from pyopenproject.business.util.filter import Filter
from datetime import datetime
import open_project_utils

if len(sys.argv) < 2:
    print("Supply AREA name")
    exit()

area = sys.argv[1]

# generate the filename for the MPP file based on the WBS area
input_file = "Tasks-" + area + ".mpp"

# generate the output filename, we convert the MPP file to JSON as an interim step
json_output_file = input_file + ".json"

# create an mpp_data object, supplying the input and output files
mpp_data = mpp_data.MppData(input_file, json_output_file)

# convert the MPP file to JSON
mpp_data.convert_mpp_to_json()

# create a tree structure to store the JSON data - easy way to preserve and traverse the heirarchy
mpp_tree = mpp_data.create_project_tree()

# WBS areas slight varied in their structure as far as depth,  this controls how deeply to traverse the tree to get "high-level activities"
# WBS1, depth = 1
# WBS3, depth = 2
# WBS4, depth = 3 -- really a depth of 2 with an added layer of tree iteration in the import

tree_depth = 0

if area == 'WBS1':
    tree_depth = 1
elif area == 'WBS2':
    tree_depth = 1
elif area == 'WBS3':
    tree_depth = 1
elif area == 'WBS4':
    tree_depth = 2
elif area == 'S_C_Ops_Program':
    tree_depth = 1

# genetates a list of activities filtered to occur before a certain date
acitivity_nodes = list(
    mpp_tree.filter_nodes(lambda x: x.data.scheduled_finish < datetime(2027, 1, 1) and mpp_tree.depth(x) == tree_depth))

# Need to create ProjectManager-export.ini to store API information
# [API Values]
# url=<API URL>
# api_key=<API_KEY>
#
#

API_config = configparser.ConfigParser()
API_config.read('ProjectManager-export.ini')
url = API_config['API Values']['url']
api_key = API_config['API Values']['api_key']

openProject_instance = OpenProject(url=url, api_key=api_key)

my_workpackage_service = openProject_instance.get_work_package_service()

my_project_service = openProject_instance.get_project_service()

# Each WBS area is a project, this finds the reference to WBS area specified at run-time
wbs_project = my_project_service.find_all([Filter("name", "=", [area])])

# deletes the existing project for importing data
if wbs_project:
    my_project_service.delete(wbs_project[0])

# Wait for Openproject to report project has been deleted - deletion is async, so it takes some time
while my_project_service.find_all([Filter("name", "=", [area])]):
    print("Waiting for deletion of existing project")
    time.sleep(5)

# generates a json file to create a new project in OpenProject for the WBS area
area_id = area.lower()
project_template = {"identifier": area_id, "name": area}

project_json = json.dumps(project_template)

new_project = Project(json.loads(project_json))
my_project_service.create(new_project)

# load the tools for adding entries to OpenProject
open_project_utils = open_project_utils.OpenProjectUtils(openProject_instance, my_workpackage_service, area)

# function to add the entries to open project - traverses mpp_tree data recursively
def process_work_packages(my_mpp_tree, my_data_node, package_type="Activity", parent_wp_id=None, parent_title=None):
    # Create the current work package

    # Stricter checking of a Milestone
    # duration should not be longer than a day
    # if current entry has milestone attribute as True and duration is longer than a day, set milestone as False to
    # avoid milestone checks in other functions
    #
    if my_data_node.data.milestone:
        duration = my_data_node.data.scheduled_finish - my_data_node.data.scheduled_start
        if duration.days <= 1:
            package_type = "Milestone"
        else:
            my_data_node.data.milestone = False
    wp = open_project_utils.create_work_package(my_data_node, package_type, parent_wp_id, parent_title)
    curr_wp = open_project_utils.update_work_package_current_dates(wp, my_data_node)
    act_wp = open_project_utils.update_work_package_actual_dates(curr_wp, my_data_node)
    open_project_utils.update_work_package_add_note(act_wp, my_data_node)

    # Process child nodes recursively
    sub_tree = my_mpp_tree.children(my_data_node.data.id)
    for child_node in sub_tree:
        process_work_packages(my_mpp_tree, child_node, "Task", wp.id, my_data_node.data.name)

    return wp


# Step through activity data in the list of activities to add entries to OpenProject using the above function.
for activity in acitivity_nodes:
    new_wp = process_work_packages(mpp_tree, activity)
    open_project_utils.check_status(new_wp)
