from DAMspy_logging import pretty_printing as gui

import os
from datetime import datetime
import csv
import pandas as pd
import json



class Logging:
    def __init__(self, log_path, run_config_id):
        self.passed = True
        self.passed_before = False
        self.unique_id = 'unknown_id'
        self.top_level_dir_path = None
        self.current_test_path = None
        self.failure_report_message = None
        self.log_path = log_path
        self.run_config_id = run_config_id
        self.log_id = None
        self.log_list = []
        self._test_id = None
        self._fail_id = None
        self._test_status = None
        self.log_dict = None
        self._test_info = []
        self.create_log_directory_top_level()
        self.test_overview_log = {
            'TEST_STANDARD': [],
            'TEST_NAME': [],
            'CONFIG_NAME':[],
            'TIMESTAMP':[],
            'PASSED': [],
        }

    def create_log_directory_top_level(self):

        date_time = datetime.now().strftime("%Y_%m_%d_%H%Mh")
        index = ''
        while True:
            try:
                top_level_dir_path = self.log_path + '\\' + date_time + '_' + self.run_config_id + index
                os.makedirs(top_level_dir_path)
                break
            except WindowsError:
                if index:
                    index = '(' + str(int(index[1:-1]) + 1) + ')'  # Append 1 to number in brackets
                else:
                    index = '(1)'

                pass  # Go and try create file again
        self.top_level_dir_path = top_level_dir_path

        return self.top_level_dir_path

    def create_test_results_path(self, standards_id, test_id):
        date_time = datetime.now().strftime("%Y_%m_%d_%H%Mh")
        index = ''
        while True:
            try:
                current_test_path = self.top_level_dir_path + '\\' + standards_id + '_' + test_id + '_' + date_time + index
                os.makedirs(current_test_path)
                self.log_id = standards_id + '_' + test_id
                break
            except WindowsError:
                if index:
                    index = '(' + str(int(index[1:-1]) + 1) + ')'  # Append 1 to number in brackets
                else:
                    index = '(1)'
                pass  # Go and try create file again

        self.current_test_path = current_test_path

    @property
    def serial_no(self):
        return self._serial_no

    # @serial_no.setter
    # def serial_no(self, serial_no):
    #     self._serial_no = serial_no
    #
    def add_serial_no(self, serial_no, is_newly_allocated=False):
        if is_newly_allocated:
            self.new_sn_allocated = True
        self._serial_no = serial_no

    @property
    def test_id(self):
        return self._test_id

    @test_id.setter
    def test_id(self, test_id):
        self._test_id = test_id

    @property
    def fail_id(self):
        return self._fail_id

    @fail_id.setter
    def fail_id(self, fail_id):
        self._fail_id = fail_id

    @property
    def test_status(self):
        return self._test_status

    @test_status.setter
    def test_status(self, test_status):
        self._test_status = test_status
        self.add_line(test_status)

    @property
    def test_info(self):
        return self._test_info

    @test_info.setter
    def test_info(self, test_info):
        self._test_info = test_info

    def fail_line(self, line, to_print=True):
        if to_print:
            fail_reason = line
            gui.print_red(fail_reason)
        self.log_list.append(line)

    def add_line(self, line, to_print=True, colour='w'):
        if to_print:
            if colour == 'w':
                print(line)
            elif colour == 'r':
                gui.print_red(line)
            elif colour == 'g':
                gui.print_green(line)
            elif colour == 'y':
                gui.print_yellow(line)
        self.log_list.append(line)

    def save_log(self):
        date_time = datetime.now().strftime("%Y_%m_%d_%H%Mh")
        pd.DataFrame(self.log_dict).to_csv(self.current_test_path + '\\Test_Results_' + self.log_id + '_' + date_time + '.csv', index=False)
        self.log_dict = None

    def save_test_overview_log(self):
        # ── Ensure all columns have equal length ─────────────────────────────────
        max_len = max(len(col) for col in self.test_overview_log.values())
        for key, lst in self.test_overview_log.items():
            if len(lst) < max_len:
                lst.extend([None] * (max_len - len(lst)))
        # ─────────────────────────────────────────────────────────────────────────



        date_time = datetime.now().strftime("%Y_%m_%d_%H%Mh")
        pd.DataFrame(self.test_overview_log).to_csv(self.top_level_dir_path + '\\' + 'Test_Result_Overview_' + self.run_config_id + '_' + date_time + '.csv', index=False)

    def test_setup_log(self, run_config, equip_config, test_location):

        date_time = datetime.now().strftime("%Y_%m_%d_%H%Mh")

        with open(self.top_level_dir_path + '\\' + 'Test_Setup_Log_' + self.run_config_id + '.txt', 'a') as f:
            print('Test Location: ', test_location, file=f)
            print('Date/Time: ', date_time + '\n', file=f)
            print('Run Configuration: \n', file=f)
            print(json.dumps(run_config, indent=4), file=f)

            # for k, v in run_config.items():
            #     print(k, v, file=f)

        with open(self.top_level_dir_path + '\\' + 'Test_Setup_Log_' + self.run_config_id + '.txt', 'a') as f:
            print('Equipment Configuration: \n', file=f)

            print(json.dumps(equip_config, indent=4), file=f)
            # for k, v in equip_config.items():
                # print(k, v, file=f)

    def test_param_log(self, test_config, test_config_opt):
        date_time = datetime.now().strftime("%Y_%m_%d_%H%Mh")
        with open(self.current_test_path + '\\' + 'Test_Parameters_' + self.log_id + '.txt', 'a') as f:
            print('Date/Time: ', date_time + '\n', file=f)
            print('Config Name: ', test_config_opt, file=f)
            print(json.dumps(test_config, indent=4), file=f)






