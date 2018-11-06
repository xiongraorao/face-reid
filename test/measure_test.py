from cluster.measure import *
import time

start = time.clock()

a = np.random.rand(10000)*100
b = np.random.rand(10000)*100
c1 = a.astype(int).reshape(1,-1)
c2 = b.astype(int).reshape(1,-1)

n = a.size
c1 = np.array(c1).reshape(1, -1)
c2 = np.array(c2).reshape(1, -1)
c1_0 = np.repeat(c1, n, axis=0)
c1_1 = np.repeat(c1.reshape(-1, 1), n, axis=1)
c2_0 = np.repeat(c2, n, axis=0)
c2_1 = np.repeat(c2.reshape(-1, 1), n, axis=1)

temp = (c1_0 == c2_0) & (c1_1 == c2_1)
a = (np.sum(temp) - np.trace(temp)) / 2
temp = (c1_0 == c2_0) & (c1_1 != c2_1)
b = (np.sum(temp) - np.trace(temp)) / 2
temp = (c1_0 != c2_0) & (c1_1 == c2_1)
c = (np.sum(temp) - np.trace(temp)) / 2
temp = (c1_0 != c2_0) & (c1_1 != c2_1)
d = (np.sum(temp) - np.trace(temp)) / 2
assert a + b + c + d == n * (n - 1) / 2.0
print('a=%d, b=%d, c=%d, d=%d', (a, b, c, d))
end = time.clock()
print('cost time: ', (end - start))


