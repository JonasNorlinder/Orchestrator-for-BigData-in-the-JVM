#!/bin/bash

# Download and extract Cassandra 4.1.0
FILE="$(dirname -- "$0")/apache-cassandra-4.1.0-bin.tar.gz"
if [ ! -f "$FILE" ]; then
  wget https://archive.apache.org/dist/cassandra/4.1.0/apache-cassandra-4.1.0-bin.tar.gz
fi

tar -xvf apache-cassandra-4.1.0-bin.tar.gz -C ./app --strip-components=1

# Patch Cassandra files
cp patch_files/bin/cassandra app/bin/cassandra
cp patch_files/conf/jvm11-clients.options app/conf/jvm11-clients.options
cp patch_files/conf/jvm11-server.options app/conf/jvm11-server.options
cp patch_files/conf/jvm-server.options app/conf/jvm-server.options
