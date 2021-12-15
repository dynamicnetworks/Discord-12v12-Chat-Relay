#!/bin/python

import asyncio
import discord
import json
import os
import re
import time

config = json.load(open("config.json"))

token = config["token"]
print("Token:", token)
channel_id = config["channel"]
print("Channel:", channel_id)

regular_expressions = []

client = discord.Client()

def get_file_size(filename):
  try:
    return os.stat(filename).st_size
  except FileNotFoundError:
    return 0

class FileMonitor:
  def __init__(self, filename, regexes, channel):
    self.filename = filename
    self.channel = channel
    self.regular_expressions = []
    for entry in regexes:
      search = entry["search"]
      replace = entry["replace"]
      try:
        self.regular_expressions.append((re.compile(search), replace))
      except re.error:
        print("Got error parsing regular expression:", search)
        raise
    self.last_size = get_file_size(self.filename)

  async def Poll(self):
    new_size = get_file_size(self.filename)
    if new_size == self.last_size:
      return False

    if new_size < self.last_size:
      self.last_size = 0
      print("File %s appears to have reset." % self.filename)

    try:
      log = open(self.filename)
    except FileNotFoundError:
      print("File %s does not exist now." % self.filename)
      # Return False so that the caller will call us again on the next poll
      # cycle. Maybe the file will exist then.
      return False

    log.seek(self.last_size)
    for line in log:
      line = line.rstrip()
      for expression in self.regular_expressions:
        result = expression[0].subn(expression[1], line, count=1)
        if result[1]:
          await self.channel.send(result[0])
          break

    self.last_size = log.tell()
    return True

@client.event
async def on_ready():
  print("%s has connected to discord" % client.user)

  channel = client.get_channel(channel_id)
  monitors = []
  for entry in config["monitor"]:
    print("Monitoring file: %s" % entry["file"])
    monitors.append(FileMonitor(entry["file"], entry["regexes"], channel))

  POLLING_PERIOD = 2

  while True:
    any_matched = False
    for monitor in monitors:
      any_matched |= await monitor.Poll()
    if not any_matched:
      await asyncio.sleep(POLLING_PERIOD)

client.run(token)
print("run is done")
