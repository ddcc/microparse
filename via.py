#! /usr/bin/env python3

import microparse
import struct

# http://review.coreboot.org/gitweb?p=coreboot.git;a=blob;f=src/cpu/via/nano/update_ucode.h;hb=HEAD
# http://review.coreboot.org/gitweb?p=coreboot.git;a=blob;f=src/cpu/via/nano/update_ucode.c;hb=HEAD

class static():
    def header(swap_endian):
        if swap_endian:
            return struct.Struct("<4sIBBHIIIIII8sI")
        else:
            return struct.Struct(">4sIBBHIIIIII8sI")

class microcode():
    def __init__(self, data, swap_endian):
        self.is_swap_endian = swap_endian

        self.parse_header(data[0 : static.header(self.is_swap_endian).size])
        self.parse_data(data[static.header(self.is_swap_endian).size : static.header(self.is_swap_endian).size + self.payload_size])

        self.raw = data[0 : self.total_size]

    def csv(self):
        return \
        microparse.static.hex8(self.update_revision) + "," + \
        microparse.static.ymd2date(self.year, self.month, self.day) + "," + \
        microparse.static.hex8(self.signature) + "," + \
        microparse.static.hex8(self.checksum) + \
        microparse.static.hex8(self.loader_revision) + "," + \
        microparse.static.hex8(self.reserved1) + "," + \
        str(int(self.payload_size) * microparse.static.data(self.is_swap_endian).size) + "," + \
        str(int(self.total_size) * microparse.static.data(self.is_swap_endian).size) + "," + \
        self.name.decode("utf-8") + "," + \
        microparse.static.hex8(self.reserved2) + "\n"

    def filename(self):
        return microparse.static.hex8(self.signature) + "_" + microparse.static.hex8(self.update_revision) + "_" + microparse.static.hex8(self.checksum)

    def size(self):
        return self.total_size

    def parse_header(self, data):
        if len(data) == static.header(self.is_swap_endian).size:
            try:
                header = static.header(self.is_swap_endian).unpack(data)
            except struct.error:
                raise Exception("Cannot unpack microcode header!")

            self.magic = header[0]
            if self.magic != b"SARR":
                raise Exception("Input microcode magic string mismatch!")
            self.update_revision = header[1]
            self.day = header[2]
            self.month = header[3]
            self.year = header[4]
            self.signature = header[5]
            self.checksum = header[6]
            self.loader_revision = header[7]
            self.reserved1 = header[8]
            self.payload_size = header[9]
            self.total_size = header[10]
            self.name = header[11]
            self.reserved2 = header[12]
        else:
            raise Exception("Input microcode header size mismatch!")

    def parse_data(self, data):
        self.data = []

        if len(data) == self.payload_size:
            for i in range(0, self.payload_size, microparse.static.data(self.is_swap_endian).size):
                try:
                    self.data.append(microparse.static.data(self.is_swap_endian).unpack(data[i : i + microparse.static.data(self.is_swap_endian).size])[0])
                except struct.error:
                    raise Exception("Cannot unpack microcode data!")
        else:
            raise Exception("Input microcode data size mismatch!")

    def calculate_checksum(self):
        # may not work correctly, needs to be checked
        checksum = self.magic + self.update_revision + self.year + self.month + self.day + self.signature + self.checksum + self.loader_revision + self.reserved1 + self.payload_size + self.total_size + self.name + self.reserved2
        for v in self.data:
            checksum += v

        return -checksum & 0xFFFFFFFF

    def __str__(self):
        #checksum = " (!)" if self.checksum != self.calculate_checksum() else ""

        return \
        microparse.static.fmt_string % ("Update Revision", microparse.static.hex8(self.update_revision)) + \
        microparse.static.fmt_string % ("Date", microparse.static.ymd2date(self.year, self.month, self.day)) + \
        microparse.static.fmt_string % ("Processor Signature", microparse.static.hex8(self.signature)) + \
        str(microparse.signature(self.signature)) + \
        microparse.static.fmt_string % ("Checksum", microparse.static.hex8(self.checksum)) + \
        microparse.static.fmt_string % ("Loader Revision", microparse.static.hex8(self.loader_revision)) + \
        microparse.static.fmt_string % ("Reserved 1", microparse.static.hex8(self.reserved1)) + \
        microparse.static.fmt_string % ("Payload Size", microparse.static.hex8(self.payload_size)) + \
        microparse.static.fmt_string % ("Total Size", microparse.static.hex8(self.total_size)) + \
        microparse.static.fmt_string % ("Name" , "\"" + self.name.decode("utf-8") + "\"") + \
        microparse.static.fmt_string % ("Reserved 2", microparse.static.hex8(self.reserved2))
