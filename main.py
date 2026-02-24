from machine import Pin, SPI
import time
import T_ETH_Lite as ETH

FIRMWARE_VERSION = 1.0
SPI_SPEED = 10_000_000
SPI_BUF_SIZE = 64
DELAY_SPI_TX_RX = 0.000_5
SPI_TX_RETRY = 3

DEBUG_MODE = False

class Error:
    COM_SPI                 = 'ERR_SPI'
    CURRENT_I2C             = 'ERR_CURRENT_I2C'
    CURRENT_LIMIT           = 'ERR_CURRENT_LIMIT'
    IMAGE_SENSOR_I2C        = 'ERR_IMAGE_SENSOR_I2C'
    IMAGE_SENSOR_ID_VALUE   = 'ERR_IMAGE_SENSOR_ID_VALUE'
    MEMORY_DIS_I2C          = 'ERR_MEMORY_DIS_I2C'
    MEMORY_EN_I2C           = 'ERR_MEMORY_EN_I2C'
    BARCODE_WRITE_I2C       = 'ERR_BARCODE_WRITE_I2C'
    SENSOR_ID_WRITE_I2C     = 'ERR_SENSOR_ID_WRITE_I2C'
    MEMORY_READ_I2C         = 'ERR_MEMORY_READ_I2C'
    VERIFY_SENSOR_ID        = 'ERR_VERIFY_SENSOR_ID'
    VERIFY_BARCODE          = 'ERR_VERIFY_BARCODE'

class Main:
    def __init__(self, server_ip, server_port):
        # self.sysLed_pico = Pin(25, Pin.OUT)
        self.barcode_sendStates = dict()
        self.isError_barcode = str()

        # region SPI
        self.spi = SPI(1, baudrate=SPI_SPEED, polarity=0, phase=0, bits=8, sck=Pin(2), mosi=Pin(1), miso=Pin(0))
        self.spi_cs_M1 = Pin(4, mode=Pin.OUT, value=1)
        self.spi_cs_M2 = Pin(5, mode=Pin.OUT, value=1)
        self.spi_cs_M3 = Pin(6, mode=Pin.OUT, value=1)
        self.spi_cs_M4 = Pin(7, mode=Pin.OUT, value=1)
        self.spi_cs_M5 = Pin(15, mode=Pin.OUT, value=1)
        self.spi_cs_M6 = Pin(16, mode=Pin.OUT, value=1)
        self.spi_cs_M7 = Pin(17, mode=Pin.OUT, value=1)
        self.spi_cs_M8 = Pin(18, mode=Pin.OUT, value=1)
        # endregion

        # region UDP/IP
        self.is_script_sending = False  # 스크립트 저장 상태
        self.script_file_name = "script.txt"
        self.client_ip = str()
        self.server_ip = server_ip
        self.server_port = server_port

        self.barcode_sendStates = {}
        # self.barcode_info = {}
        self.isSumDelay_sensorId = None
        self.delay_readSensorId = int()
        self.delay_verifyPowerOnOff = int()
        self.verifyCount = int()
        self.isRead_sensorId = False
        self.sensorId = {}

        self.isUpdateScript = False

        self.gpioIn_ipSel1 = Pin(41, Pin.IN)
        self.gpioIn_ipSel2 = Pin(40, Pin.IN)
        self.gpioIn_ipSel3 = Pin(39, Pin.IN)
        self.gpioIn_ipSel4 = Pin(38, Pin.IN)

        # self.portNumber = ''
        if self.gpioIn_ipSel1.value() == 1 and self.gpioIn_ipSel2.value() == 1 and self.gpioIn_ipSel3.value() == 1:
            self.client_ip = '192.168.1.101'
            # self.portNumber = 8001
        elif self.gpioIn_ipSel1.value() == 1 and self.gpioIn_ipSel2.value() == 1 and self.gpioIn_ipSel3.value() == 0:
            self.client_ip = '192.168.1.102'
            # self.portNumber = 8002
        elif self.gpioIn_ipSel1.value() == 1 and self.gpioIn_ipSel2.value() == 0 and self.gpioIn_ipSel3.value() == 1:
            self.client_ip = '192.168.1.103'
            # self.portNumber = 8003
        elif self.gpioIn_ipSel1.value() == 1 and self.gpioIn_ipSel2.value() == 0 and self.gpioIn_ipSel3.value() == 0:
            self.client_ip = '192.168.1.104'
            # self.portNumber = 8004

        ETH.init(self.client_ip, self.server_ip, self.server_port)
        # endregion

        # start_time = time.ticks_ms()
        self.isUpdateScript = True
        for i in range(8):
            self.sendScript(i+1)
        self.isUpdateScript = False
        # end_time = time.ticks_ms()
        # print(f'Script update elapsed time[ms]: {time.ticks_diff(end_time, start_time) / 1000}')

        # self.sendScript(1)
        # barcode = 'C9051A569000H5'
        # self.sendBarcode(5, barcode)
        # endregion

    # region time function
    def func_1ms(self):
        ret = ETH.readMessage()

    def func_10ms(self):
        pass

    def func_20ms(self):
        pass

    def func_50ms(self):
        pass

    def func_100ms(self):
        if self.isRead_sensorId:
            self.sensorId = dict()

            for key, value in self.barcode_sendStates.items():
                if value == 'failed':
                    self.sensorId[key] = Error.COM_SPI
                else:
                    self.isError_barcode = None
                    self.sensorId[key] = self.readSensorId(int(key[-1]))

                    if self.isError_barcode != None:
                        ETH.barcode_info[key] = self.isError_barcode
                        pass
                # time.sleep(0.05)

            if DEBUG_MODE:
                print(f'SensorID: {self.sensorId}')
            ETH.client.send('sensor_ID: {}'.format(self.sensorId))
            ETH.client.send('barcode_info: {}'.format(ETH.barcode_info))
            self.isRead_sensorId = False

        if ETH.isUpdateScript_mcu:
            self.updateScriptToMcu()
            ETH.isUpdateScript_mcu = False

        if ETH.isSendBarcode:
            self.sendBarcodeToMcu()
            ETH.isSendBarcode = False

    def func_500ms(self):
        pass
        # self.sysLed_pico(not self.sysLed_pico.value())

    def func_1000ms(self):
        if not ETH.client_status['connected']:
            ETH.init(self.client_ip, self.server_ip, self.server_port)
    # endregion

    # region About TCP/IP
    def updateScriptToMcu(self):
        start_time = time.ticks_ms()

        for i in range(8):
            ret = self.sendScript(i + 1)
            msg = f"Script save {ret}: MCU{i + 1}"
            ETH.client.send(msg.encode('utf-8'))

        if DEBUG_MODE:
            end_time = time.ticks_ms()
            print(f'Script update elapsed time[ms]: {time.ticks_diff(end_time, start_time) / 1000}')

    def sendBarcodeToMcu(self):
        self.barcode_sendStates = dict()

        for key, value in ETH.barcode_info.items():
            ret = self.sendBarcode(int(key[-1]), value)
            self.barcode_sendStates[key] = ret

        delay = self.delay_readSensorId + (self.delay_verifyPowerOnOff * self.verifyCount)
        time.sleep((delay + 1000) / 1000)
        self.isRead_sensorId = True

    def sendScript(self, target) -> str:
        with open('script.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                msg = line.strip().replace(' ', '').upper()
                if line[0] != ';' and line[0:2] != '\r\n' and line[0] != '\n':
                    sendBytes = b'\x01\x00' + int.to_bytes(len(msg), 2, 'big')
                    sub_msg = self.convert_hex_as_int(msg)
                    sendBytes += bytearray(sub_msg, 'utf-8')
                    while len(sendBytes) < (SPI_BUF_SIZE - 2):
                        sendBytes += b'\xFF'
                    checksum = self.getChecksum(sendBytes)
                    sendBytes += int.to_bytes(checksum, 2, 'big')
                    fail_cnt = 0
                    while True:
                        self.sendDataBySpi(sendBytes, target)
                        time.sleep(DELAY_SPI_TX_RX)
                        if b'#SCRIPT_START' in sendBytes:
                            self.delay_readSensorId = 0
                            self.delay_verifyPowerOnOff = 0
                            self.verifyCount = 0
                            time.sleep(0.05)
                        if b'#POWER_SETTING' in sendBytes:
                            self.isSumDelay_sensorId = 'POWER_SETTING'
                        elif b'#READ_SENSOR_ID' in sendBytes:
                            self.isSumDelay_sensorId = 'READ_SENSOR_ID'
                        elif b'#CHANGE_SLAVE_ADDRESS' in sendBytes:
                            self.isSumDelay_sensorId = 'CHANGE_SLAVE_ADDRESS'
                        elif b'#MEMORY_PROTECTION_DISABLE' in sendBytes:
                            self.isSumDelay_sensorId = 'MEMORY_PROTECTION_DISABLE'
                        elif b'#WRITE_BARCODE_CHECKSUM' in sendBytes:
                            self.isSumDelay_sensorId = 'WRITE_BARCODE_CHECKSUM'
                        elif b'#WRITE_BARCODE' in sendBytes:
                            self.isSumDelay_sensorId = 'WRITE_BARCODE'
                        elif b'#WRITE_SENSOR_ID_CHECKSUM' in sendBytes:
                            self.isSumDelay_sensorId = 'WRITE_SENSOR_ID_CHECKSUM'
                        elif b'#WRITE_SENSOR_ID' in sendBytes:
                            self.isSumDelay_sensorId = 'WRITE_SENSOR_ID'
                        elif b'#MEMORY_PROTECTION_ENABLE' in sendBytes:
                            self.isSumDelay_sensorId = 'MEMORY_PROTECTION_ENABLE'
                        elif b'#MODEL_INFO' in sendBytes:
                            self.isSumDelay_sensorId = 'MODEL_INFO'
                        elif b'#SLAVE_ADDRESS' in sendBytes or b':END' in sendBytes:
                            self.isSumDelay_sensorId = None
                        if self.isSumDelay_sensorId == 'POWER_SETTING':
                            if b'#POWER_SETTING' not in sendBytes:
                                self.delay_readSensorId += int(msg.split(',')[2])
                                self.delay_verifyPowerOnOff += int(msg.split(',')[2])
                        elif self.isSumDelay_sensorId == 'CHANGE_SLAVE_ADDRESS':
                            if b'#CHANGE_SLAVE_ADDRESS' not in sendBytes:
                                self.delay_readSensorId += int(msg.split(',')[6])
                        elif self.isSumDelay_sensorId == 'MEMORY_PROTECTION_DISABLE':
                            if b'#MEMORY_PROTECTION_DISABLE' not in sendBytes:
                                self.delay_readSensorId += int(msg.split(',')[6])
                        elif self.isSumDelay_sensorId == 'WRITE_BARCODE':
                            if b'#WRITE_BARCODE' not in sendBytes:
                                self.delay_readSensorId += int(msg.split(',')[6])
                        elif self.isSumDelay_sensorId == 'WRITE_BARCODE_CHECKSUM':
                            if b'#WRITE_BARCODE_CHECKSUM' not in sendBytes:
                                if msg.split(',')[1] == 'C':
                                    self.delay_readSensorId += int(msg.split(',')[7])
                                elif msg.split(',')[1] == 'W':
                                    self.delay_readSensorId += int(msg.split(',')[6])
                        elif self.isSumDelay_sensorId == 'WRITE_SENSOR_ID':
                            if b'#WRITE_SENSOR_ID' not in sendBytes:
                                self.delay_readSensorId += int(msg.split(',')[6])
                        elif self.isSumDelay_sensorId == 'WRITE_SENSOR_ID_CHECKSUM':
                            if b'#WRITE_SENSOR_ID_CHECKSUM' not in sendBytes:
                                if msg.split(',')[1] == 'C':
                                    self.delay_readSensorId += int(msg.split(',')[7])
                                elif msg.split(',')[1] == 'W':
                                    self.delay_readSensorId += int(msg.split(',')[6])
                        elif self.isSumDelay_sensorId == 'MEMORY_PROTECTION_ENABLE':
                            if b'#MEMORY_PROTECTION_ENABLE' not in sendBytes:
                                self.delay_readSensorId += int(msg.split(',')[6])
                        elif self.isSumDelay_sensorId == 'READ_SENSOR_ID':
                            if b'#READ_SENSOR_ID' not in sendBytes:
                                self.delay_readSensorId += int(msg.split(',')[6])
                        elif self.isSumDelay_sensorId == 'MODEL_INFO':
                            if b'POWER_OFF_DELAY' in sendBytes:
                                self.delay_verifyPowerOnOff = int(msg.split(':')[1])
                            if b'VERIFY_COUNT' in sendBytes:
                                self.verifyCount = int(msg.split(':')[1])
                        rxVal = self.receiveDataBySpi(SPI_BUF_SIZE, target)
                        if checksum == int.from_bytes(rxVal[SPI_BUF_SIZE - 2:], 'big'):
                            break
                        else:
                            fail_cnt += 1
                            if fail_cnt > SPI_TX_RETRY:
                                print(f'Error: Failed update script')
                                return Error.COM_SPI
                            else:
                                print(f'MCU{target}: Failed checksum, TX Retry{fail_cnt}')
        # print(self.delay_readSensorId, self.delay_verifyPowerOnOff, self.verifyCount)
        return 'finished'

    def sendBarcode(self, target, barcode) -> str:
        sendBytes = b'\x02\x00' + int.to_bytes(len(barcode), 2, 'big')
        sendBytes += bytearray(barcode, 'utf-8')

        while len(sendBytes) < (SPI_BUF_SIZE - 2):
            sendBytes += b'\xFF'

        checksum = self.getChecksum(sendBytes)
        sendBytes += int.to_bytes(checksum, 2, 'big')

        fail_cnt = 0
        while True:
            self.sendDataBySpi(sendBytes, target)
            time.sleep(DELAY_SPI_TX_RX)

            rxVal = self.receiveDataBySpi(SPI_BUF_SIZE, target)
            if checksum == int.from_bytes(rxVal[SPI_BUF_SIZE - 2:], 'big'):
                break
            else:
                fail_cnt += 1
                if fail_cnt > SPI_TX_RETRY:
                    print(f'MCU_{target} >> Error: Failed send barcode')
                    return Error.COM_SPI
                else:
                    print(f'MCU_{target} >> Warning: Failed checksum, TX Retry{fail_cnt}')
        return 'finished'

    def readSensorId(self, target) -> str:
        sendBytes = b'\x03\x00\x00\x00'

        while len(sendBytes) < (SPI_BUF_SIZE - 2):
            sendBytes += b'\xFF'

        checksum = self.getChecksum(sendBytes)
        sendBytes += int.to_bytes(checksum, 2, 'big')

        fail_cnt = 0
        while True:
            self.sendDataBySpi(sendBytes, target)
            time.sleep(DELAY_SPI_TX_RX)

            rxVal = self.receiveDataBySpi(SPI_BUF_SIZE, target)
            # print(rxVal)

            sensorId = None
            if self.getChecksum(rxVal[:-2]) == int.from_bytes(rxVal[SPI_BUF_SIZE - 2:], 'big'):
                if rxVal[1] == 0x00:
                    sensorId_len = int.from_bytes(rxVal[2:4], 'big')
                    sensorId = rxVal[4:4 + sensorId_len]

                    # print(f'Read sensor ID: {sensorId}')
                    if int.from_bytes(sensorId, 'big') == 0:
                        return Error.IMAGE_SENSOR_ID_VALUE
                    else:
                        return sensorId.hex().upper()
                elif rxVal[1] == 0x01:
                    return Error.CURRENT_LIMIT
                elif rxVal[1] == 0x02:
                    return Error.CURRENT_I2C
                elif rxVal[1] == 0x03:
                    return Error.IMAGE_SENSOR_I2C
                elif rxVal[1] == 0x04:
                    return Error.MEMORY_DIS_I2C
                elif rxVal[1] == 0x05:
                    return Error.MEMORY_EN_I2C
                elif rxVal[1] == 0x06:
                    sensorId_len = int.from_bytes(rxVal[2:4], 'big')
                    sensorId = rxVal[4:4 + sensorId_len]
                    if int.from_bytes(sensorId, 'big') == 0:
                        return Error.IMAGE_SENSOR_ID_VALUE
                    else:
                        # return Error.BARCODE_WRITE_I2C
                        self.isError_barcode = Error.BARCODE_WRITE_I2C
                        return sensorId.hex().upper()
                elif rxVal[1] == 0x07:
                    return Error.SENSOR_ID_WRITE_I2C
                elif rxVal[1] == 0x08:
                    return Error.MEMORY_READ_I2C
                elif rxVal[1] == 0x09:
                    return Error.VERIFY_SENSOR_ID
                elif rxVal[1] == 0x0A:
                    sensorId_len = int.from_bytes(rxVal[2:4], 'big')
                    sensorId = rxVal[4:4 + sensorId_len]
                    if int.from_bytes(sensorId, 'big') == 0:
                        return Error.IMAGE_SENSOR_ID_VALUE
                    else:
                        # return Error.VERIFY_BARCODE
                        self.isError_barcode = Error.VERIFY_BARCODE
                        return sensorId.hex().upper()
            else:
                fail_cnt += 1
                if fail_cnt > SPI_TX_RETRY:
                    print(f'MCU_{target} >> Error: Failed read sensor ID')
                    return Error.COM_SPI
                else:
                    print(f'MCU_{target} >> Warning: Failed checksum, TX Retry{fail_cnt}')

    def spi_chip_select(self, target, high_low):
        if target == 1:
            self.spi_cs_M1.value(high_low)
        elif target == 2:
            self.spi_cs_M2.value(high_low)
        elif target == 3:
            self.spi_cs_M3.value(high_low)
        elif target == 4:
            self.spi_cs_M4.value(high_low)
        elif target == 5:
            self.spi_cs_M5.value(high_low)
        elif target == 6:
            self.spi_cs_M6.value(high_low)
        elif target == 7:
            self.spi_cs_M7.value(high_low)
        elif target == 8:
            self.spi_cs_M8.value(high_low)

    def sendDataBySpi(self, data, target):
        if DEBUG_MODE:
            print(f'TX_{target} >> {len(data)}, {data}')

        self.spi_chip_select(target, 0)
        self.spi.write(data)
        self.spi_chip_select(target, 1)

    def receiveDataBySpi(self, length, target) -> bytes:
        self.spi_chip_select(target, 0)
        data = self.spi.read(length)
        self.spi_chip_select(target, 1)

        if DEBUG_MODE:
            print(f'RX_{target} >> {len(data)}, {data}')
        return data

    @staticmethod
    def getChecksum(data):
        checksum = 0
        for byte in data:
            checksum += byte

        return checksum & 0xFFFF
    # endregion

    @staticmethod
    def convert_hex_as_int(s):
        result = ''
        i = 0
        while i < len(s):
            if s[i:i + 2].upper() == '0X':
                j = i + 2
                hex_str = ''
                while j < len(s) and s[j].upper() in '0123456789ABCDEF':
                    hex_str += s[j]
                    j += 1
                dec = str(int(hex_str, 16))
                result += dec
                i = j
            else:
                result += s[i]
                i += 1
        return result


if __name__ == "__main__":
    cnt_ms = 0
    main = Main('192.168.1.2', 8002)

    while True:
        cnt_ms += 1

        main.func_1ms()

        if not cnt_ms % 10:
            main.func_10ms()

        if not cnt_ms % 20:
            main.func_20ms()

        if not cnt_ms % 50:
            main.func_50ms()

        if not cnt_ms % 100:
            main.func_100ms()

        if not cnt_ms % 500:
            main.func_500ms()

        if not cnt_ms % 1000:
            main.func_1000ms()

        time.sleep_ms(1)
