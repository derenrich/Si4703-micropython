# WIP - probably do not use
# Based on https://cdn.sparkfun.com/assets/f/0/9/0/1/Si4702-03-C19-1.pdf
# and https://cdn.sparkfun.com/datasheets/BreakoutBoards/AN230.pdf

# Assumes the breakout board is attached to pins 10/11 (for I2C), 12 for reset, 2 pull ups on i2c

from machine import Pin, Timer
import machine
import time
import struct

I2C_ADDRESS = 16


def shorts_to_bytearray(shorts):
    arrays = []
    for s in shorts:
        arrays.append(struct.pack(">H", s))
    return sum(arrays, b'')


def read_registers(i2c):
    regs = i2c.readfrom_mem(I2C_ADDRESS, 0, 16 * 2)
    # reading starts at 0xA goes to 0xF then loops around
    ending = regs[0:6*2]
    starting = regs[6*2:]
    return struct.unpack(">HHHHHHHHHHHHHHHH", starting + ending)

def write_registers(i2c, regs, num=None):
    # slice off read only head
    wr_regs = regs[2*2:]
    if num:
        wr_regs = wr_regs[0:num*2]
    return i2c.writeto(I2C_ADDRESS, wr_regs)
    

# startup sequence
sdio_pin = machine.Pin(10, Pin.OUT)
sdio_pin.value(0)
time.sleep(1)
reset_pin = Pin(12, Pin.OUT)
reset_pin.value(0)
time.sleep(1)
reset_pin.value(1)
time.sleep(1)

i2c = machine.I2C(1, scl=machine.Pin(11), sda=machine.Pin(10), freq=400000)


# init empty shadow register
regs = list(read_registers(i2c))

# turn on crystal
regs[0x7] |= (1 << 15)
# disable RDS (due to errata)
regs[0xF] = 0

write_registers(i2c, shorts_to_bytearray(regs))
time.sleep(1)

# turn on power
regs[0x2] = 1
write_registers(i2c, shorts_to_bytearray(regs))
time.sleep(1)

device_register = read_registers(i2c)

for i, b in enumerate(device_register):
    print(i, hex(b))


# seek
regs = list(read_registers(i2c))
regs[0x2] |= (1 << 8)
write_registers(i2c, shorts_to_bytearray(regs))

time.sleep(10)

device_register = read_registers(i2c)
for i, b in enumerate(device_register):
    print(i, hex(b))

    

