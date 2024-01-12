import json

import numpy as np
import re
from pyopenproject.model.work_package import WorkPackage
from pyopenproject.model.status import Status
from datetime import datetime

# an internal funciton to check the date format to make sure dates are in expected OpenProject format
def _check_date(dn):
    if dn is not None:
        return dn.strftime('%Y-%m-%d')
    else:
        return ""


class OpenProjectUtils:

    # initialize OpenProjectUtils object
    def __init__(self, openProject_instance, workPackage_service, wbs):
        self.openProject_instance = openProject_instance
        self.workPackage_service = workPackage_service
        self.wbs = wbs

    # funciton to create a Work Package in OpenProject
    def create_work_package(self, task_data, package_type='Activity', parent_id=None, parent_title=None):
        data_node = task_data

        # Map custom fields in OpenProject to custom fields from MPP file - required advance knowlegde of the custom fiels in the MPP files
        # TODO: find a way to automatically do this
        if data_node.data.percent_complete is not None:
            workPackage_percentageDone = int(data_node.data.percent_complete)
        else:
            workPackage_percentageDone = 0
        workPackage_customField1 = _check_date(data_node.data.Expected_Finish_Date)
        workPackage_customField2 = _check_date(data_node.data.Current_Start_Date)
        workPackage_customField3 = data_node.data.CA_Milestone_ID
        workPackage_customField4 = _check_date(data_node.data.Current_Finish_Date)
        workPackage_customField5 = data_node.data.Work_Package_ID
        workPackage_customField6 = data_node.data.Long_Name
        workPackage_customField7 = data_node.data.S_C_ID
        workPackage_customField8 = _check_date(data_node.data.actual_start)
        workPackage_customField9 = _check_date(data_node.data.actual_finish)
        workPackage_customField10 = data_node.data.KPI_Value
        workPackage_customField11 = data_node.data.Target

        # find the project in OpenProject corresponding to specified WBS Area
        project = list(filter(
            lambda x: x.name == self.wbs,
            self.workPackage_service.find_available_projects()
        ))[0].__dict__['_links']['self']

        # find the work package type - in our cases Activity, Task or Milestone
        work_package_type = list(filter(
            lambda x: x.name == package_type,
            self.openProject_instance.get_type_service().find_all()
        ))[0].__dict__['_links']['self']['href']

        # Set the status for Activities for items based on their current status in the MPP data
        workPackage_status = '/api/v3/statuses/1'
        if workPackage_percentageDone == 100 and package_type != "Activity":
            workPackage_status = '/api/v3/statuses/12'  # Closed
        if 100 > workPackage_percentageDone > 0:
            workPackage_status = '/api/v3/statuses/7'  # In Progress

        # Create a new Work Package json based on imported data to export to OpenProject
        workPackage_parent_id = None
        workPackage_parent_title = None
        if parent_id:
            workPackage_parent_id = '/api/v3/work_packages/' + str(parent_id)
            workPackage_parent_title = parent_title

        workPackage_json = {"subject": data_node.data.name,
                   "description": {"format": "markdown", "raw": "", "html": ""},
                   "scheduleManually": True,
                   "estimatedTime": None,
                   "ignoreNonWorkingDays": False,
                   "percentageDone": workPackage_percentageDone,
                   "_links": {
                       "category": {
                           "href": None
                       },
                       "type": {
                           "href": work_package_type
                       },
                       "priority": {
                           "href": "/api/v3/priorities/8",
                           "title": "Normal"
                       },
                       "project": {
                           "href": project['href']
                       },
                       "status": {
                           "href": workPackage_status,
                       },
                       "responsible": {
                           "href": None
                       },
                       "assignee": {
                           "href": None
                       },
                       "version": {
                           "href": None
                       },
                       "parent": {
                           "href": workPackage_parent_id,
                           "title": workPackage_parent_title
                       }
                   },
                   # changing mapping for production - there has to be a better way!!!
                   # "customField3": workPackage_customField1,
                   # "customField4": workPackage_customField2,
                   # "customField5": workPackage_customField3,
                   # "customField6": workPackage_customField4,
                   # "customField7": workPackage_customField5,
                   # "customField8": workPackage_customField6,
                   # "customField9": workPackage_customField7,
                   # "customField12": workPackage_customField8,
                   # "customField13": workPackage_customField9,
                   # "customField14": workPackage_customField10,
                   # "customField15": workPackage_customField11
                   "customField1": workPackage_customField1,
                   "customField2": workPackage_customField2,
                   "customField3": workPackage_customField3,
                   "customField4": workPackage_customField4,
                   "customField5": workPackage_customField5,
                   "customField6": workPackage_customField6,
                   "customField7": workPackage_customField7,
                   "customField8": workPackage_customField8,
                   "customField9": workPackage_customField9,
                   "customField10": workPackage_customField10,
                   "customField11": workPackage_customField11
                   }

        # ensure Milestones only have one date - there's no separate start and end date for Milestones in OpenProject
        if package_type == 'Milestone':
            workPackage_date = data_node.data.start.strftime('%Y-%m-%d')
            workPackage_json["date"] = workPackage_date
            print(workPackage_date)
        else:
            workPackage_startDate = data_node.data.scheduled_start.strftime('%Y-%m-%d')
            workPackage_dueDate = data_node.data.scheduled_finish.strftime('%Y-%m-%d')
            # bus_days = np.busday_count(workPackage_startDate, workPackage_dueDate) + 1
            date_diff = data_node.data.scheduled_finish - data_node.data.scheduled_start
            bus_days = date_diff.days + 1
            duration = 'P' + str(bus_days) + 'D'
            if duration == 'P0D':
                duration = 'P1D'
            workPackage_json["duration"] = duration
            workPackage_json["startDate"] = workPackage_startDate
            workPackage_json["dueDate"] = workPackage_dueDate
            print(workPackage_startDate, workPackage_dueDate)

        workPackage_json_dump = json.dumps(workPackage_json)
        my_workPackage = WorkPackage(json.loads(workPackage_json_dump))

        # try to create the Work Pacakge in OpenProject
        try:
            my_workPackage = self.workPackage_service.create(my_workPackage)
        except:
            print(package_type)
            print(my_workPackage)

        # print a message to show progress
        print(my_workPackage.subject)

        return my_workPackage

    # special date handling to try to capture our date tracking in Projectmamanger - actual date was a means of reporting of when we actually started and ended acitivities
    def update_work_package_actual_dates(self, workPackage, task_data):
        data_node = task_data
        if data_node.data.milestone:
            new_workPackage = WorkPackage({"id": workPackage.id,
                                 "lockVersion": workPackage.lockVersion,
                                 "date": workPackage.date
                                 })

            if (actual_start := _check_date(data_node.data.actual_start)) != "":
                new_workPackage.date = actual_start

            updated_workPackage = self.workPackage_service.update(new_workPackage)

            if actual_start != "" and actual_start != workPackage.date:
                start_raw_comment = f'''Milestone date changed from {workPackage.date} to {actual_start} [ACTUAL]'''
                print(start_raw_comment)
                self.workPackage_service.create_activity(updated_workPackage, start_raw_comment)

            return updated_workPackage

        else:
            new_workPackage = WorkPackage({"id": workPackage.id,
                                 "lockVersion": workPackage.lockVersion,
                                 "startDate": workPackage.startDate,
                                 "dueDate": workPackage.dueDate,
                                 "duration": workPackage.duration})

            if (actual_start := _check_date(data_node.data.actual_start)) != "":
                new_workPackage.startDate = actual_start

            if (actual_finish := _check_date(data_node.data.actual_finish)) != "":
                new_workPackage.dueDate = actual_finish

            if new_workPackage.dueDate < new_workPackage.startDate:
                print("Error in Actual Dates - " + workPackage.subject)
                return workPackage

            date_diff = datetime.strptime(new_workPackage.dueDate, '%Y-%m-%d') - datetime.strptime(new_workPackage.startDate, '%Y-%m-%d')
            bus_days = date_diff.days + 1
            # bus_days = np.busday_count(newWp.startDate, newWp.dueDate) + 1
            duration = 'P' + str(bus_days) + 'D'
            if duration == 'P0D':
                duration = 'P1D'
            new_workPackage.duration = duration

            updated_workPackage = self.workPackage_service.update(new_workPackage)

            if actual_finish != "" and actual_finish != workPackage.dueDate:
                finish_raw_comment = f'''Finish date changed from {workPackage.dueDate} to {actual_finish} [ACTUAL]'''
                print(finish_raw_comment)
                self.workPackage_service.create_activity(updated_workPackage, finish_raw_comment)

            if actual_start != "" and actual_start != workPackage.startDate:
                start_raw_comment = f'''Start date changed from {workPackage.startDate} to {actual_start} [ACTUAL]'''
                print(start_raw_comment)
                self.workPackage_service.create_activity(updated_workPackage, start_raw_comment)

            return updated_workPackage

    # special date handling to try to capture our date tracking in Projectmamanger - cuurent date was a means of reporting how we viewed the start and end dates at a specific time
    def update_work_package_current_dates(self, workPackage, task_data):
        data_node = task_data
        if data_node.data.milestone:
            new_workPackage = WorkPackage({"id": workPackage.id,
                                 "lockVersion": workPackage.lockVersion,
                                 "date": workPackage.date
                                 })

            if (current_start := _check_date(data_node.data.Current_Start_Date)) != "":
                new_workPackage.date = current_start

            final_workPackage = self.workPackage_service.update(new_workPackage)

            if current_start != "" and current_start != workPackage.date:
                start_raw_comment = f'''Milestone date changed from {workPackage.date} to {current_start} [CURRENT]'''
                print(start_raw_comment)
                self.workPackage_service.create_activity(final_workPackage, start_raw_comment)

            return final_workPackage

        else:
            new_workPackage = WorkPackage({"id": workPackage.id,
                                 "lockVersion": workPackage.lockVersion,
                                 "startDate": workPackage.startDate,
                                 "dueDate": workPackage.dueDate,
                                 "duration": workPackage.duration})

            if (current_start := _check_date(data_node.data.Current_Start_Date)) != "":
                new_workPackage.startDate = current_start

            if (current_finish := _check_date(data_node.data.Current_Finish_Date)) != "":
                new_workPackage.dueDate = current_finish

            if new_workPackage.dueDate < new_workPackage.startDate:
                print("Error in dates - " + workPackage.subject)
                return workPackage

            date_diff = datetime.strptime(new_workPackage.dueDate, '%Y-%m-%d') - datetime.strptime(new_workPackage.startDate, '%Y-%m-%d')
            bus_days = date_diff.days + 1
            # bus_days = np.busday_count(newWp.startDate, newWp.dueDate) + 1
            duration = 'P' + str(bus_days) + 'D'
            if duration == 'P0D':
                duration = 'P1D'
            new_workPackage.duration = duration

            final_workPackage = self.workPackage_service.update(new_workPackage)

            if current_finish != "" and current_finish != workPackage.dueDate:
                finish_raw_comment = f'''Finish date changed from {workPackage.dueDate} to {current_finish} [CURRENT]'''
                print(finish_raw_comment)
                self.workPackage_service.create_activity(final_workPackage, finish_raw_comment)

            if current_start != "" and current_start != workPackage.startDate:
                start_raw_comment = f'''Start date changed from {workPackage.startDate} to {current_start} [CURRENT]'''
                print(start_raw_comment)
                self.workPackage_service.create_activity(final_workPackage, start_raw_comment)

            return final_workPackage

    # function to add a comment to a work package - was done to record the above changes in dates
    def update_work_package_add_note(self, workPackage, task_data):
        data_node = task_data

        if data_node.data.notes is not None:
            print(data_node.data.notes)
            self.workPackage_service.create_activity(workPackage, data_node.data.notes)

        return workPackage

    # funciton to check the status of a Work Package and update accordingly
    def check_status(self, workPackage):
        new_workPackage = WorkPackage({"id": workPackage.id})

        my_workPackage = self.workPackage_service.find(new_workPackage)
        if "children" in my_workPackage.__dict__["_links"]:
            print("Has Children ")
            progress = self.check_workPackage_child_status(my_workPackage.__dict__["_links"]["children"])
            if progress == 100:
                new_workPackage = WorkPackage({"id": my_workPackage.id,
                                      "lockVersion": my_workPackage.lockVersion,
                                      "_links": {
                                          "status": {
                                              "href": '/api/v3/statuses/12'  # Closed
                                          }
                                      }
                                      })
                self.workPackage_service.update(new_workPackage)
            elif 100 > progress > 0:
                new_workPackage = WorkPackage({"id": my_workPackage.id,
                                      "lockVersion": my_workPackage.lockVersion,
                                      "_links": {
                                          "status": {
                                              "href": '/api/v3/statuses/7'  # In Progress
                                          }
                                      }
                                      })
                self.workPackage_service.update(new_workPackage)
        else:
            if my_workPackage.percentageDone == 100:
                new_workPackage = WorkPackage({"id": my_workPackage.id,
                                      "lockVersion": my_workPackage.lockVersion,
                                      "_links": {
                                          "status": {
                                              "href": '/api/v3/statuses/12'  # Closed
                                          }
                                      }
                                      })
                self.workPackage_service.update(new_workPackage)

    # function to check the status of children of Activities (Tasks and Milestones)
    def check_workPackage_child_status(self, children):
        regex = r"\/(\d+)"
        child_status = []
        for child in children:
            id_string = child["href"]
            child_id = re.findall(regex, id_string)[0]
            child_wp = WorkPackage({"id": child_id})
            child_wp = self.workPackage_service.find(child_wp)
            if child_wp.percentageDone == 100:
                child_status.append(1)
            else:
                child_status.append(0)
        progress = int(sum(child_status) / len(child_status) * 100)
        return progress
