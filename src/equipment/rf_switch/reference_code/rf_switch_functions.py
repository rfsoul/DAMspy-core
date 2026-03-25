import ETS_logging.text_formatter as gui

from urllib.request import urlopen
import sys

class RF_Switch_Error(Exception):

    def __init__(self, msg):
        gui.print_red(msg)



class MiniCircuits_2SP6T_A12:
    def __init__(self, switch_config):
        self.switch_config_failed = False
        self.ip_address = switch_config['IP']
        self.serial_number = None

        self.switch_settings = {
            'DISCONNECT': {'A': 'SP6TA:STATE:0', 'B': 'SP6TB:STATE:0'},
            'RX_SIG_GEN_TO_RAD': {'A': 'SP6TA:STATE:2', 'B': 'SP6TB:STATE:0'},
            'TX_HPF_700MHz': {'A': 'SP6TA:STATE:5', 'B': 'SP6TB:STATE:5'},
            'TX_HPF_300MHz': {'A': 'SP6TA:STATE:6', 'B': 'SP6TB:STATE:6'},
            'TX_NO_FILTER': {'A': 'SP6TA:STATE:4', 'B': 'SP6TB:STATE:4'}
        }

        #self.disconnect_all()
        #self.get_serial_number()
        #self.test_switch_functions()

    def get_serial_number(self):
        # Specify the IP address of the switch box
        CmdToSend = "http://" + self.ip_address + "/:" + 'SN?'

        # Send the HTTP command and try to read the result
        success = None
        try:
            HTTP_Result = urlopen(CmdToSend, timeout=1)
            PTE_Return = HTTP_Result.read()
            self.serial_number = PTE_Return
            # The switch displays a web GUI for unrecognised commands
            if len(PTE_Return) > 100:
                print("Error, command not found:", CmdToSend)
                PTE_Return = "Invalid Command!"
                success = False

            else:
                success = True

        # Catch an exception if URL is incorrect (incorrect IP or disconnected)
        except Exception as e:
            print('Exception: ', e)
            print("Error, no response from device; check IP address and connections.")
            PTE_Return = "No Response!"
            success = False

        # Return the response
        return self.serial_number

    def test_switch_functions(self):
        while True:
            selection = int(input('1. disconnect_all \n2. rx_sig_gen_to_radio \n3. TX'))
            if selection == 1:
                self.disconnect_all()
            elif selection == 2:
                self.rx_sig_gen_to_radio()
            elif selection == 3:
                tx_selection = int(input('1. TX_HPF_700MHz \n2. TX_HPF_300MHz \n3. TX_NO_FILTER'))
                if tx_selection == 1:
                    self.tx_radio_to_spec_an(filter='TX_HPF_700MHz')
                elif tx_selection == 2:
                    self.tx_radio_to_spec_an(filter='TX_HPF_300MHz')
                elif tx_selection == 3:
                    self.tx_radio_to_spec_an(filter='TX_NO_FILTER')
                elif tx_selection == 4:
                    self.tx_radio_to_spec_an(filter='PROGRAMMER_ERROR')

    def disconnect_all(self):
        gui.print_yellow('AUTO RF Switching: [DISCONNECT].')
        status_a = self.Get_HTTP_Result(self.switch_settings['DISCONNECT']['A'])  # Set switch A
        status_b = self.Get_HTTP_Result(self.switch_settings['DISCONNECT']['B'])  # Set switch B

        if (status_a or status_b) is False:
            gui.print_red('RF SWITCH ERROR')

        return True

    def rx_sig_gen_to_radio(self):
        gui.print_yellow('AUTO RF Switching: [RX_SIG_GEN_TO_RAD].')
        status_a = self.Get_HTTP_Result(self.switch_settings['RX_SIG_GEN_TO_RAD']['A'])  # Set switch A
        status_b = self.Get_HTTP_Result(self.switch_settings['RX_SIG_GEN_TO_RAD']['B'])  # Set switch B

        if (status_a or status_b) is False:
            gui.print_red('RF SWITCH ERROR')

        return True

    def tx_radio_to_spec_an(self, filter='TX_NO_FILTER'):

        if filter == 'TX_NO_FILTER':
            gui.print_yellow('AUTO RF Switching: [TX_NO_FILTER].')
            status_a = self.Get_HTTP_Result(self.switch_settings['TX_NO_FILTER']['A'])  # Set switch A
            status_b = self.Get_HTTP_Result(self.switch_settings['TX_NO_FILTER']['B'])  # Set switch B

        elif filter == 'TX_HPF_700MHz':
            gui.print_yellow('AUTO RF Switching: [TX_HPF_700MHz].')
            status_a = self.Get_HTTP_Result(self.switch_settings['TX_HPF_700MHz']['A'])  # Set switch A
            status_b = self.Get_HTTP_Result(self.switch_settings['TX_HPF_700MHz']['B'])  # Set switch B

        elif filter == 'TX_HPF_300MHz':
            gui.print_yellow('AUTO RF Switching: [TX_HPF_300MHz].')
            status_a = self.Get_HTTP_Result(self.switch_settings['TX_HPF_300MHz']['A'])  # Set switch A
            status_b = self.Get_HTTP_Result(self.switch_settings['TX_HPF_300MHz']['B'])  # Set switch B

        else:
            # gui.print_red('RF SWITCH: INVALID REQUEST')
            raise RF_Switch_Error('RF SWITCH: INVALID REQUEST')

        if (status_a or status_b) is False:
            # gui.print_red('RF SWITCH ERROR')
            raise RF_Switch_Error('RF SWITCH ERROR')

        return True

    def Get_HTTP_Result(self, CmdToSend):

        # Specify the IP address of the switch box
        CmdToSend = "http://" + self.ip_address + "/:" + CmdToSend

        # Send the HTTP command and try to read the result
        success = None
        try:
            HTTP_Result = urlopen(CmdToSend, timeout=1)
            PTE_Return = HTTP_Result.read()
            # The switch displays a web GUI for unrecognised commands
            if len(PTE_Return) > 100:
                print ("Error, command not found:", CmdToSend)
                PTE_Return = "Invalid Command!"
                success = False

            else:
                success = True

        # Catch an exception if URL is incorrect (incorrect IP or disconnected)
        except Exception as e:
            print('Exception: ', e)
            print ("Error, no response from device; check IP address and connections.")
            PTE_Return = "No Response!"
            success = False

        # Return the response
        return success


class RF_Switch:

    def __new__(cls, switch_config):
        switch_class = None

        if switch_config['model'] == 'MiniCircuits_2SP6T_A12':
            switch_class = MiniCircuits_2SP6T_A12(switch_config)

        if switch_class.switch_config_failed:
            return False
        else:
            return switch_class


# if __name__ == '__main__':
#     my_config = {
#         'model': 'MiniCircuits_2SP6T_A12',
#         'IP': '10.0.22.136'
#     }
#     rf_switch = RF_Switch(switch_config=my_config)
#     rf_switch.test_switch_functions()
