from machine import Pin, SPI
import errno
import network
import socket
import ujson
import time

DEBUG_MODE = True

client = None
client_status = {'connected': False}
script = b''
# cntTimeout = 0
isUpdateScript = False
isUpdateScript_mcu = False
isSendBarcode = False
barcode_info = {}

# W5x00 chip init
def init(client_ip, server_ip, server_port) -> None:
    global client

    # SPI 및 W5500 초기화
    spi = SPI(0, 10_000_000, polarity=0, phase=0, mosi=Pin(12), miso=Pin(11), sck=Pin(10))
    eth = network.WIZNET5K(spi, Pin(9), Pin(14))  # spi,cs,reset pin
    eth.active(True)

    eth.ifconfig((client_ip, '255.255.255.0', '192.168.0.1', '8.8.8.8'))
    if DEBUG_MODE:
        print("Network config:", eth.ifconfig())

    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setblocking(True)
            # client.settimeout(100)
            client.connect((server_ip, server_port))
            break
        except OSError as e:
            if e.errno != errno.ECONNABORTED:
                print(e)

    client.setblocking(False)
    client_status['connected'] = True
    if DEBUG_MODE:
        print(f"Connected to server: {server_ip}:{server_port}")
        # client.send(bytes("W5500_EVB_PICO","utf-8"))

def readMessage():
    global client, script, isUpdateScript, isUpdateScript_mcu
    global isSendBarcode, barcode_info
    # global cntTimeout

    try:
        rxData = client.recv(1024)
        # print(rxData)

        if b'# Script_Start\n' in rxData:
            # cntTimeout = 0
            script = b''
            isUpdateScript = True
        elif b'barcode_info:' in rxData:
            text = rxData.decode('utf-8').replace("'", '"')
            dict_part = text.split(":", 1)[1].strip()
            barcode_info = ujson.loads(dict_part)
            isSendBarcode = True
            # print('BardCode:', barcode_info)

        if isUpdateScript:
            script += rxData

            if b'# Script_End\n' in rxData:
                with open("script.txt", "w") as f:
                    f.write(script)
                isUpdateScript_mcu = True
                isUpdateScript = False
                client.send(bytes("Updated script","utf-8"))

            # cntTimeout += 1
            # if cntTimeout > 3000:
            #     isUpdateScript = False

        return None

    except Exception as e:
        if e.errno != errno.EAGAIN:
            print(f'Exception >> {e}')

        if client_status['connected']:
            if e.errno == errno.ECONNRESET or e.errno == errno.EBADF:
                print("Disconnected socket")
                client_status['connected'] = False


def sendMessage(msg: str) -> None:
    pass
