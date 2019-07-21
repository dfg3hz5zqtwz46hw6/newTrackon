from collections import OrderedDict
from socket import AF_INET, AF_INET6, inet_ntop
from struct import unpack

TOK_DICT = b'd'
TOK_LIST = b'l'
TOK_INT = b'i'
TOK_END = b'e'
TOK_STR_SEP = b':'


def bdecode(data):
    bdecoded_response = Decoder(data).decode()
    response = {}
    for key, value in bdecoded_response.items():
        if isinstance(key, bytes):
            response[key.decode()] = value
        else:
            response[key] = value

    if 'peers' in response:
        response['peers'] = extract_compact_peers(response['peers'], AF_INET)

    if 'peers6' in response:
        response['peers6'] = extract_compact_peers(response['peers6'], AF_INET6)

    for key, value in response.items():
        if isinstance(value, bytes):
            response[key] = value.decode()

    return response


def extract_compact_peers(peers, ip_type):
    # only handles compact peer info, possible future TODO: support dict info
    if ip_type == AF_INET:
        peer_length = 6
    else:
        peer_length = 18
    peers_list = [peers[i:i + peer_length] for i in range(0, len(peers), peer_length)]
    peers_tuples = []
    for p in peers_list:
        ip = inet_ntop(ip_type, p[:peer_length - 2])  # unpack the IP bytes
        port = unpack("!H", p[peer_length - 2:])[0]  # unpack the port bytes
        peers_tuples.append({'IP': ip, 'port': port})
    return peers_tuples


class Decoder:

    def __init__(self, data):
        if not isinstance(data, bytes):
            raise TypeError("'data' must be 'bytes'")
        self.index = 0
        self.data = data

    def decode(self):
        # decode the bencoded data
        c = self.peek()  # get the next character
        if c is None:
            raise EOFError()
        elif c == TOK_DICT:
            self.read(1)  # read the token
            return self.decode_dict()
        elif c == TOK_LIST:
            self.read(1)  # read the token
            return self.decode_list()
        elif c == TOK_INT:
            self.read(1)  # read the token
            return self.decode_int()
        elif c in b'0123456789':  # the number indicates start of str (tells len(str))
            return self.decode_str()
        elif c == TOK_END:
            return None
        else:
            raise RuntimeError()

    # get the next byte
    def peek(self):
        if self.index + 1 >= len(self.data):  # index is passed the end of the data
            return None
        return self.data[self.index: self.index + 1]

    # read the data for the length
    def read(self, length):
        if self.index + length > len(self.data):
            raise RuntimeError()
        result = self.data[self.index: self.index + length]
        self.index += length
        return result

    # read until the first occurence of the token
    def read_until(self, token):
        # get the index of the token starting from where last left off
        loc = self.data.find(token, self.index)
        if loc == -1:  # token not found
            raise RuntimeError()
        # token found, loc is the index of it
        result = self.data[self.index: loc]
        self.index = loc + 1  # move index to just past loc read up to
        return result

    # decodes bencoded data into a Python OrderedDict
    def decode_dict(self):
        result = OrderedDict()
        while self.data[self.index: self.index + 1] != TOK_END:
            key = self.decode()  # decode the key
            item = self.decode()  # decode the item
            result[key] = item  # add the key item pair to the dict
        self.read(1)  # read the end token
        return result

    # decodes bencoded data into a Python list
    def decode_list(self):
        result = []
        while self.data[self.index: self.index + 1] != TOK_END:
            item = self.decode()  # decode an item
            result.append(item)  # add to the list
        self.read(1)  # read the end token
        return result

    # decode bencoded data into a Python int
    def decode_int(self):
        return int(self.read_until(TOK_END))  # read until the end token

    # decode the bencoded data into a Python string
    def decode_str(self):
        length = int(self.read_until(TOK_STR_SEP))  # get the length of str
        return self.read(length)  # read that length
