# server settings
ADDR = '0.0.0.0'
PORT = 8080
DEFAULT_TIMEOUT = 1.0

# maps hostname to another server/port combo in a tuple
# example: "www.example.com": ('internal_hostname', <port>)
HOST_MAP = {
}

# redirect url if target host is not found in HOST_MAP
HNF_REDIRECT = ''

# recv buffer size
BUFSIZE = 1024 * 1024

# path to key and certificate files for HTTPS
KEYFILE = ''
CERTFILE = ''
