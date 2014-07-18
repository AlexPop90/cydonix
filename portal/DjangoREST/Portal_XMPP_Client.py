__author__ = 'alex'
import logging

from sleekxmpp import ClientXMPP
from sleekxmpp.xmlstream import ET, tostring

from datetime import datetime

import sqlite3
import re

import threading

import ConfigParser
from optparse import OptionParser
import sys
import os




class PortalXMPP(ClientXMPP):
    def __init__(self, jid, password, sensor_bot_jid, sqlite3_db_path, polling):
        ClientXMPP.__init__(self, jid, password)

        # Setting the sender jid and the receiver jid
        self.sender_jid = jid
        self.sensor_bot_jid = sensor_bot_jid

        # The path to the sqlite3 database
        self.DB_path = sqlite3_db_path

        # The sensor value polling interval in seconds
        self.polling = polling

        # The sensor_types cache
        self.sensor_types_dict = {}
        self.sensor_types_cache_init()

        # Setting the session_start event handler to a method that prints "Started" at session start
        self.add_event_handler("session_start", self.session_start)

        # Connecting bot
        self.connect()

        # Sending bot presence
        self.send_presence()

        # Adding "message" event handler
        self.add_event_handler("message", self.receive_m)

        self.register_plugin('xep_0060')
        self.node = 'cydonix_node'
        self.pubsub_server = "pubsub.teseus.integrasoft.ro"
        self.add_event_handler('pubsub_publish', self._publish)

        try:
            #self.subscribe()
            #self.unsubscribe()
            self.process(block=True)
        except KeyboardInterrupt:
            self.send_thread.cancel()
        '''try:
            # Creating and starting first send thread
            t = threading.Timer(1, self.send_m)
            t.start()

            # Starting to process incoming messages
            self.process(block=True)

        except KeyboardInterrupt:
            self.send_thread.cancel()'''

    def send_m(self):
        self.connection = sqlite3.connect(self.DB_path)
        self.cursor = self.connection.cursor()

        self.cursor.execute("SELECT sensor_type FROM portal_sensors")
        sensor_types = self.cursor.fetchall()

        s = ''

        for s_type in sensor_types:
            str_s_type = str(s_type[0])
            s += str_s_type+' '

        s = s.strip()

        # Sending custom 'get' requests for sensor data
        self.send_message(mto=self.sensor_bot_jid,
                          mbody='GET '+s, mtype='normal', mfrom=self.sender_jid)

        print("Sent 'GET "+s+"'")
        self.process(block=False)

        try:
            # Creating and starting the next send thread before the current one terminates
            self.send_thread = threading.Timer(self.polling, self.send_m)
            self.send_thread.start()
        except KeyboardInterrupt:
            self.send_thread.cancel()

    def receive_m(self, msg):
        self.connection = sqlite3.connect(self.DB_path)
        self.cursor = self.connection.cursor()

        #print("Received '"+str(msg['body'])+"'")
        print("Received '"+str(msg)+"'")

        # Parsing the received message, with regular expressions
        s_sensor_type_names = re.split(' ', str(msg['body']))

        for s_sensor_type_name_item in s_sensor_type_names:
            s_sensor_type_name = re.search("([\w]+(?==))", s_sensor_type_name_item).group(1)
            re_value = re.search("((?<==)[\w]+[.]*[\w]*)", s_sensor_type_name_item).group(1)
            if re_value == 'True':
                value = 1
            elif re_value == 'False':
                value = 0
            else:
                value = float(re_value)

            print("sensor_type = '"+s_sensor_type_name+"' value = '"+str(value)+"'")

            commit = 0
            sensor_type = 0

            # Fetching the id of the sensor_type with the name = s_sensor_type_name if it exists in the cache
            found_in_cache = 0
            for item in self.sensor_types_dict:
                if item == s_sensor_type_name:
                    found_in_cache = 1
                    sensor_type = self.sensor_types_dict[item]
                    commit = 1

            # Fetching the id of the sensor_type with the name = s_sensor_type_name if it exists in the database
            if found_in_cache == 0:
                self.cursor.execute("SELECT id FROM portal_sensors WHERE sensor_type='"+s_sensor_type_name+"'")
                sensor_type = self.cursor.fetchone()
                if str(sensor_type) != 'None':
                    sensor_type = sensor_type[0]
                    self.sensor_types_dict[s_sensor_type_name] = sensor_type  # Add found id to cache
                    commit = 1
                else:
                    print("There is no sensor of type '"+s_sensor_type_name+"'")
                    commit = 0

            if commit > 0:
                utc_time = datetime.utcnow().isoformat(' ')  # UTC date and time in ISO 8601 format

                s_sensor_type = str(sensor_type)
                s_value = str(value)
                s_time = "'"+str(utc_time)+"'"

                print("INSERT INTO portal_sensordata (sensor_id, value, timestamp)"
                      "VALUES ( " + s_sensor_type + ", " + s_value + ", " + s_time+")")

                # Adding the received sensor data to the appropriate table
                self.cursor.execute("INSERT INTO portal_sensordata (sensor_id, value, timestamp)"
                                    "VALUES ( " + s_sensor_type + ", " + s_value + ", " + s_time+")")
                self.connection.commit()

                print("Commited")
            else:
                print("Not commited")

    def session_start(self, event):
        print("Started")

    def sensor_types_cache_init(self):
        self.connection = sqlite3.connect(self.DB_path)
        self.cursor = self.connection.cursor()

        self.cursor.execute("SELECT * FROM portal_sensors")
        sensor_types = self.cursor.fetchall()
        for item in sensor_types:
            self.sensor_types_dict[str(item[1])] = item[0]

    def subscribe(self):
        try:
            result = self['xep_0060'].subscribe(self.pubsub_server, self.node)
            print(result)
            print('Subscribed %s to node %s' % (self.boundjid.bare, self.node))
        except:
            logging.error('Could not subscribe %s to node %s' % (self.boundjid.bare, self.node))

    def unsubscribe(self):
        try:
            result = self['xep_0060'].unsubscribe(self.pubsub_server, self.node)
            print('Unsubscribed %s from node %s' % (self.boundjid.bare, self.node))
        except:
            logging.error('Could not unsubscribe %s from node %s' % (self.boundjid.bare, self.node))

    def _publish(self, msg):
        """Handle receiving a publish item event."""
        print('Published item %s to %s:' % (
            msg['pubsub_event']['items']['item']['id'],
            msg['pubsub_event']['items']['node']))
        data = msg['pubsub_event']['items']['item']['payload']
        msg_2 = {}
        if data is not None:
            str_data = tostring(data)
            erase = 'abc'
            while True:
                try:
                    erase = re.search("(<.*?>)", str_data).group(1)
                except AttributeError:
                    break
                str_data = str_data.replace(erase, '')

            msg_2['body'] = str_data

            # The 2 ways to insert new data in the sensor data table
            self.receive_m(msg_2)  # 1) get data from notification
            #self.send_m()  # 2) send get data and parse received message
        else:
            print('No item content')


# Setting up the command line arguments
optp = OptionParser()

optp.add_option('-c', '--config=FILE', dest="conf_file", help='configuration FILE')
optp.add_option('-d', '--debug', help='set logging to DEBUG', action='store_const',
                dest='loglevel', const=logging.DEBUG, default=logging.disable('INFO'))
optp.add_option('-l', '--log=FILE', dest="log_file", help='log messages to FILE')

opts, args = optp.parse_args()
print(opts.log_file)
logging.basicConfig(level=opts.loglevel,
                    format='%(levelname)-8s %(message)s', filename=opts.log_file, filemode='a')

# If configuration file does not exist the script will terminate
if not (os.path.isfile(str(opts.conf_file))):
    print "The configuration file does not exist"
    sys.exit()

# Reading data from the configuration file
conf = ConfigParser.ConfigParser()
conf.read(opts.conf_file)

sender_jid = conf.get("XMPP", "sender_jid")
sender_pass = conf.get("XMPP", "sender_pass")
receiver_jid = conf.get("XMPP", "receiver_jid")
sqlite3_DB_path = conf.get("XMPP", "sqlite3_DB_path")
polling_interval = int(conf.get("XMPP", "polling"))

# Initializing the XMPP bot
xmpp = PortalXMPP(sender_jid, sender_pass, receiver_jid, sqlite3_DB_path, polling_interval)