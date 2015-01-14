#!/usr/bin/env python
"""Checks the status (availability, logged-in players) on a Minecraft server.

Example:
    $ %(prog)s host [port]
    available, 3/5 online: mf, dignity, viking

    or

    >>> McServer('my.mcserver.com').Update().player_names_sample
    frozenset(['mf', 'dignity', 'viking'])

Based on:
    https://gist.github.com/barneygale/1209061
Protocol reference:
    http://wiki.vg/Server_List_Ping
"""

import argparse
import json
import logging
import socket
import struct

DEFAULT_PORT = 25565
TIMEOUT_SEC = 5.0


class McServer:

  def __init__(self, host, port=DEFAULT_PORT):
    self._host = host
    self._port = int(port)
    self._Reinit()

  def _Reinit(self):
    self._available = False
    self._num_players_online = 0
    self._max_players_online = 0
    self._player_names_sample = frozenset()

  def Update(self):
    # print "Updating "+  self._host + "/" + str(self._port)
    try:
      json_dict = GetJson(self._host, port=self._port)
    except (socket.error, ValueError) as e:
      self._Reinit()
      logging.debug(e)
      return self
    self._num_players_online = json_dict['players']['online']
    self._max_players_online = json_dict['players']['max']    
    self._available = True
    return self

  @property
  def available(self):
    return self._available

  @property
  def num_players_online(self):
    return self._num_players_online

  @property
  def max_players_online(self):
    return self._max_players_online

  @property
  def player_names_sample(self):
    return self._player_names_sample


def GetJson(host, port=DEFAULT_PORT):
  """
  Example response:

  json_dict = {
    u'players': {
      u'sample': [
        {u'id': u'6a0c2570-274f-36b8-97b0-898868ba6827', u'name': u'mf'}
      ],
      u'max': 20,
      u'online': 1,
    },
    u'version': {u'protocol': 5, u'name': u'1.7.8'},
    u'description': u'1.7.8',
    u'favicon': u'data:image/png;base64,iVBORw0K...YII=',
  }
  """
  # Open the socket and connect.
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.settimeout(TIMEOUT_SEC)
  s.connect((host, port))

  # Send the handshake + status request.
  s.send(_PackData('\x00\x00' + _PackData(host.encode('utf8'))
                   + _PackPort(port) + '\x01'))
  s.send(_PackData('\x00'))

  # Read the response.
  unused_packet_len = _UnpackVarint(s)
  unused_packet_id = _UnpackVarint(s)
  expected_response_len = _UnpackVarint(s)

  data = ''
  while len(data) < expected_response_len:
    data += s.recv(1024)

  s.close()

  return json.loads(data.decode('utf8'))


def _UnpackVarint(s):
  num = 0
  for i in range(5):
    next_byte = ord(s.recv(1))
    num |= (next_byte & 0x7F) << 7*i
    if not next_byte & 0x80:
      break
  return num


def _PackVarint(num):
  remainder = num
  packed = ''
  while True:
    next_byte = remainder & 0x7F
    remainder >>= 7
    packed += struct.pack('B', next_byte | (0x80 if remainder > 0 else 0))
    if remainder == 0:
      break
  return packed


def _PackData(data_str):
  return _PackVarint(len(data_str)) + data_str


def _PackPort(port_num):
  return struct.pack('>H', port_num)


if __name__ == '__main__':
  logging.basicConfig(
      format='%(levelname)s %(asctime)s %(filename)s:%(lineno)s: %(message)s',
      level=logging.DEBUG)

  summary_line, _, main_doc = __doc__.partition('\n\n')
  parser = argparse.ArgumentParser(
      description=summary_line,
      epilog=main_doc,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument(
      '--port', type=int, default=DEFAULT_PORT,
      help='defaults to %d' % DEFAULT_PORT)
  parser.add_argument('host')
  args = parser.parse_args()

  logging.info('querying %s:%d', args.host, args.port)

  server = McServer(args.host, port=args.port)
  server.Update()
  if server.available:
    logging.info(
        'available, %d/%d online: %s',
        server.num_players_online, server.max_players_online,
        ', '.join(server.player_names_sample))
  else:
    logging.info('unavailable')
