
from quixstreams import Application
from quixstreams.models.serializers.protobuf import ProtobufDeserializer
import gen.models.traffic_send_analyze_pb2 as analyze_pb
import gen.models.host_info_pb2 as host_info_pb
app = Application(broker_address='localhost:9092', auto_offset_reset='earliest')

topic_traffic_packets = app.topic("traffic.packets", value_deserializer=ProtobufDeserializer(msg_type=analyze_pb.PacketInfo))
topic_hots = app.topic("traffic.hosts", value_deserializer=ProtobufDeserializer(msg_type=host_info_pb.HostInfo))


# sdf = app.dataframe(topic=topic_traffic_packets)
# sdf = sdf.print()

sdf1 = app.dataframe(topic=topic_hots)
sdf1 = sdf1.print()


app.run()