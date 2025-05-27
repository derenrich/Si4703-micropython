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
    

def read_rds(i2c, tries=300):
    try_num = 0
    while True:
        regs = list(read_registers(i2c))
        rds_ready = regs[0xA] & (1 << 15)
        if rds_ready:
            dat = (regs[0xC], regs[0xD], regs[0xE], regs[0xF], try_num)
            return dat
        # manual advises polling every ~40ms
        time.sleep(0.040)
        try_num += 1
        if try_num > tries:
            break
    return None


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

# enable RDS
regs = list(read_registers(i2c))
regs[0x4] |= (1 << 12)
write_registers(i2c, shorts_to_bytearray(regs))
    
    
# configure seek params
regs = list(read_registers(i2c))
regs[0x5] = (regs[0x5] & 0xff) | (0x5F << 8)
write_registers(i2c, shorts_to_bytearray(regs))

# seek to a real chan
while True:
    #print("seeking")
    regs = list(read_registers(i2c))
    regs[0x2] |= (1 << 8)
    write_registers(i2c, shorts_to_bytearray(regs))
    time.sleep(0.10)
    timeout = 0
    lock = False
    while True:
        regs = list(read_registers(i2c))
        seek_done = regs[0xA] & (1 << 14)
        if seek_done:
            print("seek done")
            lock = True
            break
        
        seek_fail = regs[0xA] & (1 << 13)
        if seek_fail:
            print("seek fail")
            break
        
        afc_rail = regs[0xA] & (1 << 12)
        #if afc_rail:
        #    print("afc rail")
        #    break
        
        chan = (regs[0xB] & 0b111111111)
        freq_khz = chan * 200 + 87500
        
        rssi = regs[0xA] & 0xff
        
        time.sleep(1)
        timeout += 1
        #print(freq_khz, 'khz', rssi, 'db', hex(regs[0xA]))
        if rssi > 28:
            lock = True
            #print(freq_khz, 'khz', rssi, 'db', hex(regs[0xA]))
            break        
        if timeout > 4:
            break
    if lock:
        #print("seek done")
        rds_dat = read_rds(i2c, 200)
        
        regs = list(read_registers(i2c))
        chan = (regs[0xB] & 0b111111111)
        freq_khz = chan * 200 + 87500        
        rssi = regs[0xA] & 0xff
        
        if rds_dat:
            PIC = rds_dat[0]
            print(freq_khz, 'khz', rssi, 'db', hex(PIC), rds_dat)
        else:
            print(freq_khz, 'khz', rssi, 'db', "no rds")

    # clear seek bit
    regs = list(read_registers(i2c))
    regs[0x2] &= ~(1 << 8)
    write_registers(i2c, shorts_to_bytearray(regs))
    time.sleep(0.30)





    



    

