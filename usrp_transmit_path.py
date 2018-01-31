#
# Copyright 2009 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

from gnuradio import gr
import transmit_path
from gnuradio import eng_notation
from uhd_interface import uhd_transmitter
def add_freq_option(parser):
    """
    Hackery that has the -f / --freq option set both tx_freq and rx_freq
    """
    def freq_callback(option, opt_str, value, parser):
        parser.values.rx_freq = value
        parser.values.tx_freq = value

    if not parser.has_option('--freq'):
        parser.add_option('-f', '--freq', type="eng_float",
                          action="callback", callback=freq_callback,
                          help="set Tx and/or Rx frequency to FREQ [default=%default]",
                          metavar="FREQ")

def add_options(parser, expert):
    add_freq_option(parser)
    uhd_transmitter.add_options(parser)
    transmit_path.transmit_path.add_options(parser, expert)
    expert.add_option("", "--tx-freq", type="eng_float", default=None,
                          help="set transmit frequency to FREQ [default=%default]", metavar="FREQ")
    parser.add_option("-v", "--verbose", action="store_true", default=False)

class usrp_transmit_path(gr.hier_block2):
    def __init__(self, modulator_class, options):
        '''
        See below for what options should hold
        '''
        gr.hier_block2.__init__(self, "usrp_transmit_path",
                gr.io_signature(0, 0, 0),                    # Input signature
                gr.io_signature(0, 0, 0)) # Output signature
        tx_path = transmit_path.transmit_path(modulator_class, options)
        for attr in dir(tx_path): #forward the methods
            if not attr.startswith('_') and not hasattr(self, attr):
                setattr(self, attr, getattr(tx_path, attr))
        #setup usrp
        args = modulator_class.extract_kwargs_from_options(options)
        symbol_rate = options.bitrate / modulator_class(**args).bits_per_symbol()        
        self.sink = uhd_transmitter(options.args, symbol_rate,
            options.samples_per_symbol,
            options.tx_freq, options.tx_gain,
            options.spec, options.antenna,
            options.verbose)
        #connect
        self.connect(tx_path, self.sink)


