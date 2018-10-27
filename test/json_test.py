import json

# 1. 对简单对象的转换

class A:
    def __init__(self, name, age):
        self.name = name
        self.age = age

def a_2_json(obj):
    return {
        'name': obj.name,
        'age': obj.age
    }

a = A('jack', 18)
json_str = json.dumps(a, default=a_2_json)
print(json_str)

# 2. 复杂对象的转换

class Customer:
  def __init__(self, name, grade, age, home, office):
    self.name = name
    self.grade = grade
    self.age = age
    self.address = Address(home, office)
  def __repr__(self):
    return repr((self.name, self.grade, self.age, self.address.home, self.address.office))
class Address:
  def __init__(self, home, office):
    self.home = home
    self.office = office
  def __repr__(self):
    return repr((self.name, self.grade, self.age))
customers = [
    Customer('john', 'A', 15, '111', 'aaa'),
    Customer('jane', 'B', 12, '222', 'bbb'),
    Customer('dave', 'B', 10, '333', 'ccc'),
    ]
json_str = json.dumps(customers, default=lambda o: o.__dict__, sort_keys=True, indent=4)
print(json_str)