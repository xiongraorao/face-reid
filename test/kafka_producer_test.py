from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic, NewPartitions
from util.mykafka import Kafka
'''
api doc: 
https://github.com/dpkp/kafka-python/blob/master/README.rst
'''


def create_topic(topic_name):
    client = KafkaAdminClient(bootstrap_servers='192.168.1.6:19092')
    topic = NewTopic(topic_name, 3, 3)
    client.create_topics([topic])

def delete_topic(topic_name):
    client = KafkaAdminClient(bootstrap_servers='192.168.1.6:19092')
    client.delete_topics(topic_name)

def produce():
    producer = KafkaProducer(bootstrap_servers='192.168.1.6:19092')
    for _ in range(10):
        future = producer.send('test2', b'hello, mmp')
        result = future.get(timeout=60)  # block util a single message is sent
        print(result)


def consume():
    consumer = KafkaConsumer(bootstrap_servers='192.168.1.6:19092',
                             auto_offset_reset='earliest',
                             consumer_timeout_ms=1000)
    consumer.subscribe('test2')
    # consumer = KafkaConsumer('test', bootstrap_servers='192.168.1.6:19092',auto_offset_reset = 'earliest')
    for msg in consumer:
        print(msg)


if __name__ == '__main__':
    # t1 = threading.Thread(target=produce)
    # t2 = threading.Thread(target=consume)
    # #t1.start()
    # t2.start()
    #produce()
    #consume()
    #create_topic()
    #delete_topic(["test2"])
    kafka = Kafka(bootstrap_servers='192.168.1.6:19092')
    #kafka.create_topics([('test1', 3, 3), ('test2', 3, 3)])
    import time
    for i in range(200):
        kafka.send('test1', 'test1 message: ' + str(i * 4))
        kafka.send('test2', 'test2 message: ' + str(i * 2))
        print('send: ', i)
        time.sleep(1)

