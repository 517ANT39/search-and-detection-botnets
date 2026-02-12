

create table info_processes_running_in_servers (
   username String,
   cmdline Array(String),
   memory_info Tuple(UInt32, UInt32, UInt32, UInt32, UInt32, UInt32, UInt32), -- По порядку поля памяти
   environ Map(String, String),
   name String,
   cpu_percent Float32,
   open_files Nested(
       path String,
       fd UInt32,
       inode UInt32,
       mode Char,
       size UInt32
   ),
   pid UInt32,
   connections Array(String),
   io_counters Map(String,UInt32),
   host_id String
) ENGINE = Kafka
  SETTINGS kafka_broker_list = 'kafka:9092',
          kafka_topic_list = 'processes_info',
          kafka_group_name = 'info_processes_running_in_servers_consumer',
          kafka_format = 'JSONEachRow';

CREATE TABLE data_info_processes_running_in_servers (
    username String,
    cmdline Array(String),
    memory_info Tuple(UInt32, UInt32, UInt32, UInt32, UInt32, UInt32, UInt32), -- По порядку поля памяти
    environ Map(String, String),
    name String,
    cpu_percent Float32,
    open_files Nested(
       path String,
       fd UInt32,
       inode UInt32,
       mode Char,
       size UInt32
    ),
    pid UInt32,
    connections Array(String),
    io_counters Tuple(UInt32, UInt32, UInt32, UInt32, UInt32, UInt32), -- IO статистики
    host_id String
    ) ENGINE = MergeTree
ORDER BY (host_id);

create MATERIALIZED VIEW consume_info_processes_running_in_servers TO data_info_processes_running_in_servers
AS
SELECT
    *
FROM info_processes_running_in_servers;