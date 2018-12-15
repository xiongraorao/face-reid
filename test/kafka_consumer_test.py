from util import Kafka

kafka = Kafka(bootstrap_servers='192.168.1.6:19092')
topics = ['test1', 'test2']
topics = ['grab_image']
consumer = kafka.get_consumer(topics, group_id='default')
for message in consumer:
    print("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                         message.offset, message.key,
                                         message.value))
# while True:
#     try:
#         message = next(consumer, 10)
#         print("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
#                                          message.offset, message.key,
#                                          message.value))
#     except StopIteration:
#         print('stop error')