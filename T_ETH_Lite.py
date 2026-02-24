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

eth = None




# W5x00 chip init
def init(client_ip, server_ip, server_port, spi=None) -> None:
    """
    ESP32S3 + W5500:
      network.LAN(phy_addr=1, phy_type=network.PHY_W5500, spi=spi, cs=9, reset=14, int=13)

    spi: (optional) pass an already-created SPI object to avoid "SPI host already in use"
    """
    global client, eth

    # --- Ethernet init (create only once) ---
    # T-ETH-Lite ESP32S3 W5500 pinmap: sck=10, mosi=12, miso=11
    spi = SPI(1, 10_000_000, polarity=0, phase=0, mosi=Pin(12), miso=Pin(11), sck=Pin(10))
    eth = network.LAN(phy_addr=1, phy_type=network.PHY_W5500, spi=spi, cs=9, reset=14, int=13)
    eth.active(True)

    # 기존 static ip 유지 (네 환경이 192.168.0.1 게이트웨이 기준이므로 그대로 둠)
    eth.ifconfig((client_ip, '255.255.255.0', '192.168.0.1', '8.8.8.8'))
    if DEBUG_MODE:
        print("Network config:", eth.ifconfig())

    # --- TCP connect (기존 로직 유지) ---
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setblocking(True)
            client.connect((server_ip, server_port))
            break
        except OSError as e:
            if e.errno != errno.ECONNABORTED:
                print(e)

    client.setblocking(False)
    client_status['connected'] = True
    if DEBUG_MODE:
        print(f"Connected to server: {server_ip}:{server_port}")



#
# # W5x00 chip init
# def init(client_ip, server_ip, server_port) -> None:
#     global client
#
#     # SPI 및 W5500 초기화
#     spi = SPI(1, 10_000_000, polarity=0, phase=0, mosi=Pin(12), miso=Pin(11), sck=Pin(10))
#     eth = network.LAN(spi, Pin(9), Pin(14))  # spi,cs,reset pin
#     eth.active(True)
#
#     eth.ifconfig((client_ip, '255.255.255.0', '192.168.0.1', '8.8.8.8'))
#     if DEBUG_MODE:
#         print("Network config:", eth.ifconfig())
#
#     while True:
#         try:
#             client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             client.setblocking(True)
#             # client.settimeout(100)
#             client.connect((server_ip, server_port))
#             break
#         except OSError as e:
#             if e.errno != errno.ECONNABORTED:
#                 print(e)
#
#     client.setblocking(False)
#     client_status['connected'] = True
#     if DEBUG_MODE:
#         print(f"Connected to server: {server_ip}:{server_port}")
#         # client.send(bytes("W5500_EVB_PICO","utf-8"))

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
