from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from kafka.admin import KafkaAdminClient, NewTopic, NewPartitions


class Kafka:
    def __init__(self, bootstrap_servers):
        self.bootstrap_servers = bootstrap_servers
        self.client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers)

    def create_topics(self, new_topics):
        '''
        create a list of topics
        :param topic_name: a list of tuple including 'topic_name', 'partition_number', 'replica_factor'
        :param num_partitions:
        :param replica_factor:
        :return:
        '''
        topics = []
        for item in new_topics:
            topic = NewTopic(item[0], item[1], item[2])
            topics.append(topic)
        self.client.create_topics(topics)

    def delete_topics(self, topic_names):
        '''
        delete a list of topics
        :param topic_names: a list of topics
        :type list
        :return:
        '''
        self.client.delete_topics(topic_names)

    def send(self, topic_name, msg):
        '''
        produce message to this topic
        :param topic_name: topic name
        :param msg: message string
        :type str
        :return:
        '''
        self.producer.send(topic_name, msg.encode('utf-8'))

    def get_consumer(self, topic_names, group_id = None):
        '''
        a list of topics for subscription
        :param topic_names:
        :return: topic to list of records since the last fetch for
        subscribed list of topics and partitions
        :type dict
        '''
        consumer = KafkaConsumer(bootstrap_servers = self.bootstrap_servers, group_id = group_id)
        consumer.subscribe(topic_names)
        return consumer

    def pause(self, consumer, topic, partition):
        consumer.pause(TopicPartition(topic=topic, partition=partition))

    def resume(self, consumer, topic, partition):
        consumer.resume(TopicPartition(topic=topic, partition=partition))

if __name__ == '__main__':
    kafka = Kafka(bootstrap_servers='192.168.1.6:19092')
    topics = ['test1', 'test2']
    topics = ['grab_image']
    consumer = kafka.get_consumer(topics, group_id='test')
    # for message in consumer:
    #     print("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
    #                                     message.offset, message.key,
    #                                     message.value))
    while True:
        try:
            message = next(consumer, 10)
            print("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                             message.offset, message.key,
                                             message.value))
        except StopIteration:
            print('stop error')




