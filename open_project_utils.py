import json

import numpy as np
import re
from pyopenproject.model.work_package import WorkPackage
from pyopenproject.model.status import Status
from datetime import datetime


def _check_date(dn):
    if dn is not None:
        return dn.strftime('%Y-%m-%d')
    else:
        return ""


class OpenProjectUtils:

    def __init__(self, op, wpSer, wbs):
        self.op = op
        self.wpSer = wpSer
        self.wbs = wbs

    def create_work_package(self, task_data, package_type='Activity', parent_id=None, parent_title=None):
        dn = task_data

        if dn.data.percent_complete is not None:
            wp_percentageDone = int(dn.data.percent_complete)
        else:
            wp_percentageDone = 0
        wp_customField1 = _check_date(dn.data.Expected_Finish_Date)
        wp_customField2 = _check_date(dn.data.Current_Start_Date)
        wp_customField3 = dn.data.CA_Milestone_ID
        wp_customField4 = _check_date(dn.data.Current_Finish_Date)
        wp_customField5 = dn.data.Work_Package_ID
        wp_customField6 = dn.data.Long_Name
        wp_customField7 = dn.data.S_C_ID
        wp_customField8 = _check_date(dn.data.actual_start)
        wp_customField9 = _check_date(dn.data.actual_finish)
        wp_customField10 = dn.data.KPI_Value
        wp_customField11 = dn.data.Target

        project = list(filter(
            lambda x: x.name == self.wbs,
            self.wpSer.find_available_projects()
        ))[0].__dict__['_links']['self']

        work_package_type = list(filter(
            lambda x: x.name == package_type,
            self.op.get_type_service().find_all()
        ))[0].__dict__['_links']['self']['href']

        wp_status = '/api/v3/statuses/1'
        if wp_percentageDone == 100 and package_type != "Activity":
            wp_status = '/api/v3/statuses/12'  # Closed
        if 100 > wp_percentageDone > 0:
            wp_status = '/api/v3/statuses/7'  # In Progress

        wp_parent_id = None
        wp_parent_title = None
        if parent_id:
            wp_parent_id = '/api/v3/work_packages/' + str(parent_id)
            wp_parent_title = parent_title

        wp_json = {"subject": dn.data.name,
                   "description": {"format": "markdown", "raw": "", "html": ""},
                   "scheduleManually": True,
                   "estimatedTime": None,
                   "ignoreNonWorkingDays": False,
                   "percentageDone": wp_percentageDone,
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
                           "href": wp_status,
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
                           "href": wp_parent_id,
                           "title": wp_parent_title
                       }
                   },
                   # changing mapping for production - there has to be a better way!!!
                   # "customField3": wp_customField1,
                   # "customField4": wp_customField2,
                   # "customField5": wp_customField3,
                   # "customField6": wp_customField4,
                   # "customField7": wp_customField5,
                   # "customField8": wp_customField6,
                   # "customField9": wp_customField7,
                   # "customField12": wp_customField8,
                   # "customField13": wp_customField9,
                   # "customField14": wp_customField10,
                   # "customField15": wp_customField11
                   "customField1": wp_customField1,
                   "customField2": wp_customField2,
                   "customField3": wp_customField3,
                   "customField4": wp_customField4,
                   "customField5": wp_customField5,
                   "customField6": wp_customField6,
                   "customField7": wp_customField7,
                   "customField8": wp_customField8,
                   "customField9": wp_customField9,
                   "customField10": wp_customField10,
                   "customField11": wp_customField11
                   }

        if package_type == 'Milestone':
            wp_date = dn.data.start.strftime('%Y-%m-%d')
            wp_json["date"] = wp_date
            print(wp_date)
        else:
            wp_startDate = dn.data.scheduled_start.strftime('%Y-%m-%d')
            wp_dueDate = dn.data.scheduled_finish.strftime('%Y-%m-%d')
            # bus_days = np.busday_count(wp_startDate, wp_dueDate) + 1
            date_diff = dn.data.scheduled_finish - dn.data.scheduled_start
            bus_days = date_diff.days + 1
            duration = 'P' + str(bus_days) + 'D'
            if duration == 'P0D':
                duration = 'P1D'
            wp_json["duration"] = duration
            wp_json["startDate"] = wp_startDate
            wp_json["dueDate"] = wp_dueDate
            print(wp_startDate, wp_dueDate)

        test_json = json.dumps(wp_json)
        wP = WorkPackage(json.loads(test_json))

        try:
            wP = self.wpSer.create(wP)
        except:
            print(package_type)
            print(wP)

        print(wP.subject)

        return wP

    def update_work_package_actual_dates(self, wp, task_data):
        dn = task_data
        if dn.data.milestone:
            newWp = WorkPackage({"id": wp.id,
                                 "lockVersion": wp.lockVersion,
                                 "date": wp.date
                                 })

            if (actual_start := _check_date(dn.data.actual_start)) != "":
                newWp.date = actual_start

            updated_wP = self.wpSer.update(newWp)

            if actual_start != "" and actual_start != wp.date:
                start_raw_comment = f'''Milestone date changed from {wp.date} to {actual_start} [ACTUAL]'''
                print(start_raw_comment)
                self.wpSer.create_activity(updated_wP, start_raw_comment)

            return updated_wP

        else:
            newWp = WorkPackage({"id": wp.id,
                                 "lockVersion": wp.lockVersion,
                                 "startDate": wp.startDate,
                                 "dueDate": wp.dueDate,
                                 "duration": wp.duration})

            if (actual_start := _check_date(dn.data.actual_start)) != "":
                newWp.startDate = actual_start

            if (actual_finish := _check_date(dn.data.actual_finish)) != "":
                newWp.dueDate = actual_finish

            if newWp.dueDate < newWp.startDate:
                print("Error in Actual Dates - " + wp.subject)
                return wp

            date_diff = datetime.strptime(newWp.dueDate, '%Y-%m-%d') - datetime.strptime(newWp.startDate, '%Y-%m-%d')
            bus_days = date_diff.days + 1
            # bus_days = np.busday_count(newWp.startDate, newWp.dueDate) + 1
            duration = 'P' + str(bus_days) + 'D'
            if duration == 'P0D':
                duration = 'P1D'
            newWp.duration = duration

            updated_wP = self.wpSer.update(newWp)

            if actual_finish != "" and actual_finish != wp.dueDate:
                finish_raw_comment = f'''Finish date changed from {wp.dueDate} to {actual_finish} [ACTUAL]'''
                print(finish_raw_comment)
                self.wpSer.create_activity(updated_wP, finish_raw_comment)

            if actual_start != "" and actual_start != wp.startDate:
                start_raw_comment = f'''Start date changed from {wp.startDate} to {actual_start} [ACTUAL]'''
                print(start_raw_comment)
                self.wpSer.create_activity(updated_wP, start_raw_comment)

            return updated_wP

    def update_work_package_current_dates(self, wp, task_data):
        dn = task_data
        if dn.data.milestone:
            newWp = WorkPackage({"id": wp.id,
                                 "lockVersion": wp.lockVersion,
                                 "date": wp.date
                                 })

            if (current_start := _check_date(dn.data.Current_Start_Date)) != "":
                newWp.date = current_start

            final_wP = self.wpSer.update(newWp)

            if current_start != "" and current_start != wp.date:
                start_raw_comment = f'''Milestone date changed from {wp.date} to {current_start} [CURRENT]'''
                print(start_raw_comment)
                self.wpSer.create_activity(final_wP, start_raw_comment)

            return final_wP

        else:
            newWp = WorkPackage({"id": wp.id,
                                 "lockVersion": wp.lockVersion,
                                 "startDate": wp.startDate,
                                 "dueDate": wp.dueDate,
                                 "duration": wp.duration})

            if (current_start := _check_date(dn.data.Current_Start_Date)) != "":
                newWp.startDate = current_start

            if (current_finish := _check_date(dn.data.Current_Finish_Date)) != "":
                newWp.dueDate = current_finish

            if newWp.dueDate < newWp.startDate:
                print("Error in dates - " + wp.subject)
                return wp

            date_diff = datetime.strptime(newWp.dueDate, '%Y-%m-%d') - datetime.strptime(newWp.startDate, '%Y-%m-%d')
            bus_days = date_diff.days + 1
            # bus_days = np.busday_count(newWp.startDate, newWp.dueDate) + 1
            duration = 'P' + str(bus_days) + 'D'
            if duration == 'P0D':
                duration = 'P1D'
            newWp.duration = duration

            final_wP = self.wpSer.update(newWp)

            if current_finish != "" and current_finish != wp.dueDate:
                finish_raw_comment = f'''Finish date changed from {wp.dueDate} to {current_finish} [CURRENT]'''
                print(finish_raw_comment)
                self.wpSer.create_activity(final_wP, finish_raw_comment)

            if current_start != "" and current_start != wp.startDate:
                start_raw_comment = f'''Start date changed from {wp.startDate} to {current_start} [CURRENT]'''
                print(start_raw_comment)
                self.wpSer.create_activity(final_wP, start_raw_comment)

            return final_wP

    def update_work_package_add_note(self, wp, task_data):
        dn = task_data

        if dn.data.notes is not None:
            print(dn.data.notes)
            self.wpSer.create_activity(wp, dn.data.notes)

        return wp

    def check_status(self, wp):
        new_wp = WorkPackage({"id": wp.id})

        my_wp = self.wpSer.find(new_wp)
        if "children" in my_wp.__dict__["_links"]:
            print("Has Children ")
            progress = self.check_wp_child_status(my_wp.__dict__["_links"]["children"])
            if progress == 100:
                new_wp = WorkPackage({"id": my_wp.id,
                                      "lockVersion": my_wp.lockVersion,
                                      "_links": {
                                          "status": {
                                              "href": '/api/v3/statuses/12'  # Closed
                                          }
                                      }
                                      })
                self.wpSer.update(new_wp)
            elif 100 > progress > 0:
                new_wp = WorkPackage({"id": my_wp.id,
                                      "lockVersion": my_wp.lockVersion,
                                      "_links": {
                                          "status": {
                                              "href": '/api/v3/statuses/7'  # In Progress
                                          }
                                      }
                                      })
                self.wpSer.update(new_wp)
        else:
            if my_wp.percentageDone == 100:
                new_wp = WorkPackage({"id": my_wp.id,
                                      "lockVersion": my_wp.lockVersion,
                                      "_links": {
                                          "status": {
                                              "href": '/api/v3/statuses/12'  # Closed
                                          }
                                      }
                                      })
                self.wpSer.update(new_wp)

    def check_wp_child_status(self, children):
        regex = r"\/(\d+)"
        child_status = []
        for child in children:
            id_string = child["href"]
            child_id = re.findall(regex, id_string)[0]
            child_wp = WorkPackage({"id": child_id})
            child_wp = self.wpSer.find(child_wp)
            if child_wp.percentageDone == 100:
                child_status.append(1)
            else:
                child_status.append(0)
        progress = int(sum(child_status) / len(child_status) * 100)
        return progress
