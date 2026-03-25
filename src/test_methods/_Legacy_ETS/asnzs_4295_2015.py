from test_methods.radio_tests_common import RadioTest


class ASNZS_4295_2015(RadioTest):
    def __init__(self, equip_config, test_equipment, radio_eeprom, radio_param, radio_ctrl, test_results):
        super().__init__(equip_config, test_equipment, radio_eeprom, radio_param, radio_ctrl, test_results=test_results)

    def test_1(self):

        self.test_results.test_id = 'ASNZS Test 1'
        print('Testing ASNZS Test 1...')
        return True

    def test_2(self):
        self.test_results.test_id = 'ASNZS Test 2'
        print('Testing ASNZS Test 2...')
        return True

