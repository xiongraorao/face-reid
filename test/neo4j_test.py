from py2neo import Graph,Node, Relationship


# 1. 连接数据库

test_graph = Graph('http://192.168.1.6:7474', username='neo4j', password='123456')

test_graph.delete_all() # 清空库

# 2. 创建节点

a = Node('Person', name='郭靖', favorite='射箭')
b = Node('Person', name='黄蓉')
a['kungfu'] = '降龙十八掌'
a['born'] = '牛家村'
b['kungfu'] = '打狗棒'
b['born'] = '桃花岛'
r = Relationship(a, 'love', b)
s = a | b | r
test_graph.create(s)

# 3. 查询

data1 = test_graph.run('MATCH(p:Person) return p')
data = data1.data()
print('data = ', data[0])
print('type: ', type(data[0]))
