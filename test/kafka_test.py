from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.client import KafkaClient

'''
api doc: 
https://github.com/dpkp/kafka-python/blob/master/README.rst
'''

def create_topic():
    client = KafkaClient(bootstrap_servers='192.168.1.6:19092')
    #client.add_topic('test2')
    print(client.check_version())


def produce():
    producer = KafkaProducer(bootstrap_servers = '192.168.1.6:19092')
    for _ in range(10):
        future = producer.send('test', b'hello, mmp')
        result = future.get(timeout=60) # block util a single message is sent
        print(result)

def consume():
    consumer = KafkaConsumer(bootstrap_servers='192.168.1.6:19092',
                             auto_offset_reset='earliest',
                             consumer_timeout_ms=1000)
    consumer.subscribe('test')
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
    create_topic()


