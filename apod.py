import socket
import ssl
import time
import json
import sys
import os

def make_request(host_name, request, port = 443, duration = 0):
    # create an ssl context
    context = ssl.create_default_context()
    # a byte buffer that will store the data
    data = b''
    # create a TCP socket
    with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as sock:
        # connect to the NASA API
        sock.connect((host_name, port))
        with context.wrap_socket(sock, server_hostname=host_name) as ssock:
            if duration <= 0:
                # make a non-persistent HTTP request
                req = 'GET {} HTTP/1.0\r\nHost: {}\r\n\r\n'.format(request, host_name)
                ssock.sendall(req.encode('UTF-8'))
                # byte buffer
                while True:
                    temp = b''
                    temp = ssock.recv(1024)
                    if len(temp) > 0:
                        data += temp
                    if len(temp) == 0:
                        break
            else:
                # make socket non-blocking and perform a persistent HTTP request
                req = 'GET {} HTTP/1.1\r\nHost: {}\r\n\r\n'.format(request, host_name)
                ssock.sendall(req.encode('UTF-8'))
                # make the socket non-blocking and check the stream for data until duration seconds passed
                ssock.setblocking(0)
                last = time.time()
                total = 0.0
                while True:
                    temp = b''
                    try:
                        temp = ssock.recv(1024)
                    except ssl.SSLWantReadError:
                        pass
                    now = time.time()
                    dt = now - last
                    total += dt
                    last = now
                    if len(temp) > 0:
                        data += temp
                    if total >= duration:
                        break
                ssock.setblocking(1)
    return data

def parse_url(url):
    # take the index after the protocol
    begin = url.index('://')
    # take the index before the top level domain
    end = url.index('.gov')
    # take the name of the host
    host_name = url[begin + len('://') : end + len('.gov')]
    request = url[end + len('.gov'):]
    return host_name, request

def write_explanation(path, expl):
    # write the explanation
    with open(path, 'w') as file:
        words = expl.split(' ')
        text = ''
        for i in range(len(words)):
            if (i+1) % 20 == 0:
                text += '\n'
            text += words[i]
            if i != len(words) - 1:
                text += ' '
        file.write(text)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        read_from_disk = False
    elif len(sys.argv) == 2:
        read_from_disk = True
    else:
        print('USSAGE: python apod.py (optional path_to_json)')
        sys.exit(1)
    
    abs_path =  os.path.realpath(__file__)
    prefix = abs_path[:abs_path.index(__file__)]
    jsonobj = None

    if read_from_disk:   
        with open(sys.argv[1], 'r') as file:
            jsonobj = json.load(file)
    else:
        response = make_request('api.nasa.gov', '/planetary/apod?api_key=DEMO_KEY').decode(encoding='UTF-8')
        # load the json
        jsonobj = json.loads(response[response.index("{"):])
    # take the url
    url = jsonobj['url']
    # parse the image url
    host_name, response = parse_url(url)
    # take the title of the image
    title = jsonobj['title'].replace(' ','_').lower()
    # write the explanation
    expl = jsonobj['explanation']
    write_explanation(prefix + title + '_expl.txt', expl)
    # make a request to download the image
    data = make_request(host_name, response)
    # take the data after the HTTP header
    image_data = data[data.index(b'\r\n\r\n') + len('\r\n\r\n'):]
    # write the image
    with open(prefix + title + '.jpg', 'wb') as file:
        file.write(image_data)