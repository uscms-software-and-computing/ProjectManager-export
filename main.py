import configparser
import json
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

input_file = "Tasks-" + area + ".mpp"

json_output_file = input_file + ".json"

mpp_data = mpp_data.MppData(input_file, json_output_file)

mpp_data.convert_mpp_to_json()

mpp_tree = mpp_data.create_project_tree()

# WBS1, depth = 1
# WBS3, depth = 2
# WBS4, depth = 3 -- really a depth of 2 with an added layer of tree iteration in the import

tree_depth = 0

if area == 'WBS1':
    tree_depth = 1
elif area == 'WBS3':
    tree_depth = 1
elif area == 'WBS4':
    tree_depth = 2
elif area == 'S_C_Ops_Program':
    tree_depth = 1

date_nodes = list(
    mpp_tree.filter_nodes(lambda x: x.data.scheduled_finish < datetime(2027, 1, 1) and mpp_tree.depth(x) == tree_depth))

config = configparser.ConfigParser()
config.read('ProjectManager-export.ini')
url = config['API Values']['url']
api_key = config['API Values']['api_key']

op = OpenProject(url=url, api_key=api_key)

my_wpSer = op.get_work_package_service()

my_proSer = op.get_project_service()

wbs_project = my_proSer.find_all([Filter("name", "=", [area])])

if wbs_project:
    my_proSer.delete(wbs_project[0])

area_id = area.lower()
project_template = {"identifier": area_id, "name": area}

project_json = json.dumps(project_template)

new_project = Project(json.loads(project_json))
my_proSer.create(new_project)

open_project_utils = open_project_utils.OpenProjectUtils(op, my_wpSer, area)


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


# Usage:
for data_node in date_nodes:
    process_work_packages(mpp_tree, data_node)
