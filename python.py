import math

a = 5  # 二进制为 101
result = a << 1  # 向左移动 1 位，结果为 10，二进制为 1010，即 10
print(result)  # 输出 10


a = 3.7
result = math.ceil(a)  # 将浮点数转换为整数，结果为 3
print(result)  # 输出 3


from random import *
print(uniform(2,5))
print(randrange(3,20,3))



a="wwww.bupt.edu.cn"
print(a.strip("cnw"))


list=["a","b","c","d"]
a="#".join(list)
print(a)


x='abababab'
print(x.find("ab",2))

s = "a bbbb c"
print(s.replace("b","*"))

x="abcabcabc"
print(x.count("ab",3,5),x.count("ab",3,4))