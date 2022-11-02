# FIXME: this fails because it evaluates as (A^B)^C
# @test symbol-expr x (A{XOR}B{XOR}C)
a = 1
b = 2
x = bool(a) ^ bool(b) ^ bool(3)
