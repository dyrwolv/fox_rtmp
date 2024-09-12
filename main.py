# Dyrwolv's python based overwatch utilities.
# src/main.py

from rtmp_server.server import rtmp


# from utils.logger import log


def main():
    ip_address = "0.0.0.0"
    port = 1935

    rtmp(ip_address, port)


if __name__ == '__main__':
    main()
