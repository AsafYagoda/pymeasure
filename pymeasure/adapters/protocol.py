#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2022 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging

from .adapter import Adapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def to_bytes(command):
    """Change `command` to a bytes object"""
    if isinstance(command, (bytes, bytearray)):
        return command
    elif command is None:
        return b""
    elif isinstance(command, str):
        return command.encode("utf-8")
    elif isinstance(command, (list, tuple)):
        return bytes(command)
    elif isinstance(command, (int, float)):
        return str(command).encode("utf-8")
    raise TypeError(f"Invalid input of type {type(command).__name__}.")


class ProtocolAdapter(Adapter):
    """ Adapter class testing command exchange without instrument hardware.

    :param list of lists comm_pairs: List of message pairs. First message is
        the write one, the second one is the read message.
        'None' indicates that a pair member (write or read) does not exist.
    :param kwargs: TBD key-word arguments
    """

    def __init__(self, comm_pairs=[], preprocess_reply=None, **kwargs):
        """Generate the adapter and initialize internal buffers."""
        assert isinstance(comm_pairs, (list, tuple)), (
            "Parameter comm_pairs has to be a list or tuple.")
        super().__init__(preprocess_reply=preprocess_reply, **kwargs)
        self._read_buffer = b""
        self._write_buffer = b""
        self.comm_pairs = comm_pairs
        self._index = 0

    def write(self, command):
        """Compare the command with the expected one and fill the read."""
        self.write_bytes(to_bytes(command))
        assert self._write_buffer == b"", (
            f"Written bytes '{self._write_buffer}' do not match expected "
            f"'{self.comm_pairs[self._index][0]}'.")

    def write_bytes(self, content):
        """Write the bytes `content`. If a command is full, fill the read."""
        self._write_buffer += content
        p_write, p_read = self.comm_pairs[self._index]
        if self._write_buffer == to_bytes(p_write):
            assert self._read_buffer == b"", (
                f"Unread response '{self._read_buffer}' present when writing. "
                "Read the response or enable the property's 'check_set_errors'")
            # Clear the write buffer
            self._write_buffer = b""
            self._read_buffer = to_bytes(p_read)
            self._index += 1

    def read(self):
        """Return an already present or freshly fetched read buffer as a string."""
        return (self.read_bytes(-1) + self.read_bytes(1)).decode("utf-8")

    def read_bytes(self, count):
        """Read `count` number of bytes."""
        if self._read_buffer:
            read = self._read_buffer[:count]
            self._read_buffer = self._read_buffer[count:]
            return read
        else:
            p_write, p_read = self.comm_pairs[self._index]
            assert p_write is None, "Unexpected read without prior write."
            self._read_buffer = to_bytes(p_read)[count:]
            self._index += 1
            return to_bytes(p_read)[:count]

    # TODO: Harmonise ask being write+read (i.e., remove from VISAAdapter),
    #   use protocol tests to confirm it works correctly
    # TODO: Remove all now-unnecessary ask() implementations -
    #   read and write implementations should have all (test this)
    # TODO: Implement over-the-wire message-traffic logging here, first
    # TODO: Check timing impact of non-firing logging messages
    # TODO: Roll out message-traffic logging to all Adapters, try to DRY