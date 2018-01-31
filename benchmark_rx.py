#!/usr/bin/env python

# By Yanzhi Dou
# Simple implementation of Dynamic Spectrum Access with Gnuradio and USRP


from gnuradio import gr, gru
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from optparse import OptionParser
from numpy import random
import random, time, struct, sys, math
from datetime import datetime

# from current dir
#from transmit_path import transmit_path
#from receive_path import receive_path

import usrp_transmit_path
import usrp_receive_path


global sync_status,mode,ch,data_packet_delivery_count,n_rcvd, n_right
sync_status = False

#Defining modes of operation
# sync: the two nodes are trying to rendezvous on a common channel
# traffic: the two node are communicating information to each other
mode = "sync" #Default mode is sync
data_packet_delivery_count = 0

class my_top_block(gr.top_block):

    def __init__(self, mod_class, demod_class,
            rx_callback, options_tx,options_rx):

        gr.top_block.__init__(self)
        self.rxpath = usrp_receive_path.usrp_receive_path(demod_class, rx_callback, options_rx)
        self.txpath = usrp_transmit_path.usrp_transmit_path(mod_class, options_tx)
        self.connect(self.txpath);
        self.connect(self.rxpath);


def main():

    global stats_array, count_array, time_array, n_rcvd
    global n_right, sync_status, mode, ch, data_packet_delivery_count
    global n_attempts
    data_packet_delivery_count_previous = 0
    n_rcvd = 0
    n_right = 0
    n_attempts = 5
    threshold = 0.01

    count_array = [ 0, 0, 0, 0, 0]
    time_array = [ 0, 0, 0, 0, 0]
    stats_array = [ 0, 0, 0, 0, 0,0,0,0,0,0,0,0,0,0,0]


    def send_pkt(self, payload='', eof=False):
        return self.txpath.send_pkt(payload, eof)

    def get_freq_tx():

        return 2.44*1e9

    def get_freq_rx():
#        return 8,900e6
        # Convert hop_freq to our unique channel list
        channel = int(random.choice([1,7,8,14]))
            
        if channel < 8:
            hop_freq = float(1e6 * (850+(channel-1)*5))#setting the centre freq frequency for sending packets
        else:
            hop_freq = float(1e6 * (900+(channel-8)*5))#setting the centre freq frequency for sending packets    
        
        stats_array[channel] = stats_array[channel] + 1
        print "\nChannel DSA Selection Statistics (Channel #: Number times selected)"
        print "1: ", stats_array[1], " 7: ",stats_array[7], " 8: ",stats_array[8], " 14: ", stats_array[14]
        return channel,hop_freq #returning the channel number and hop frequency
    

    def rx_callback(ok, payload):
        
        global n_rcvd, n_right,sync_status,mode,ch,data_packet_delivery_count
        ########################## sync ####################################
        if mode == "sync":
            if ok:
                print "SYNC:GOT CHANNEL PACKET"
                (pktno,) = struct.unpack('!H', payload[0:2])
                (sync_signal,) = struct.unpack('!s', payload[2]) 
                (data_channel,) = struct.unpack('!H', payload[3:5])
                                  
                if str(sync_signal) == 'o' and str(data_channel) == str(ch):
                    sync_status = True
                    #tb.stop()
                    print "SYNC:RECEIVE CONFIRM PACKET...LINK ESTABLISHED"                           
                if str(sync_signal) == 's' and str(data_channel) == str(ch): 
                    print "SYNC:SEND CONFIRM PACKET"
                    sync_status = True
                    data = 'o'
                    pktno=0
                    ack_payload = struct.pack('!HsH', pktno & 0xffff,data,ch & 0xffff) #+ data
                    send_pkt(tb,ack_payload) #sending back the acknowledgement
        ###################################################################
            
        ######################### traffic #################################
        if mode == "traffic":
            if ok: 
                (data_header,) = struct.unpack('!s', payload[0])
                if data_header == 'd':
		    #print "TRAFFIC:SEND ACK"
                    data_packet_delivery_count = data_packet_delivery_count +1
                    comm = struct.unpack('!14s', payload[1:15])
                    data = 'dI am fine.....' #Sending this message
                    payload = struct.pack('!15s', data)
                    send_pkt(tb,payload)
                
        ##############################################################

        n_rcvd += 1
        if ok:
            n_right += 1

    mods = digital.modulation_utils.type_1_mods()
    demods = digital.modulation_utils.type_1_demods()


    #setting up the tx options parser

    parser_tx = OptionParser(option_class=eng_option, conflict_handler="resolve")
    
    parser_tx.add_option("-m", "--modulation", type="choice", choices=mods.keys(),
            default='gmsk',help="Select modulation from: %s [default=%%default]" 
            % (', '.join(mods.keys()),))
    parser_tx.add_option("-s", "--size", type="eng_float", default=1500,
                      help="set packet size [default=%default]")
    parser_tx.add_option("-M", "--megabytes", type="eng_float", default=1.0,
                      help="set megabytes to transmit [default=%default]")
    parser_tx.add_option("","--discontinuous", action="store_true", default=False,
                      help="enable discontinous transmission (bursts of 5 packets)") 
    parser_tx.add_option("","--from-file", default=None,
                          help="use file for packet contents")

 
    expert_grp_tx = parser_tx.add_option_group("Expert_tx")
    dsa_grp = parser_tx.add_option_group("DSA Options")

        
    dsa_grp.add_option("-T", "--threshold", type="eng_float", default=0.01,
                          help="set primary user sensing energy threshold [default=%default]")
  
    usrp_transmit_path.add_options(parser_tx, expert_grp_tx)
    parser_tx.remove_option('-f');
    #parser_tx.remove_option('--tx-freq');

    for mod in mods.values():
        mod.add_options(expert_grp_tx)


    (options_tx, args_tx) = parser_tx.parse_args ()

    if len(args_tx) != 0:
        parser_tx.print_help()
        sys.exit(1)
    
    ############# Setting some default values for tx side of the block
    options_tx.tx_freq = 2.44e9
    options_tx.samples_per_symbol =  2
    options_tx.modulation = 'gmsk'
    options_tx.fusb_block_size = 4096
    options_tx.fusb_nblocks = 16
    options_tx.bitrate = 0.0125e6
    #############

    parser_rx = OptionParser (option_class=eng_option, conflict_handler="resolve")
    expert_grp_rx = parser_rx.add_option_group("Expert_rx")
    usrp_receive_path.add_options(parser_rx, expert_grp_rx)
    
    parser_rx.remove_option('-f');
 
    (options_rx, args_rx) = parser_rx.parse_args ()

    ############# Setting some default values for rx side of the block
    options_rx.rx_freq = 900e6 #setting default rx_freq value
    options_rx.samples_per_symbol =  2
    options_rx.modulation = 'gmsk'
    options_rx.fusb_block_size = 4096
    options_rx.fusb_nblocks = 16
    options_rx.bitrate = 0.0125e6
    #############


    print "[[ Using the RANDOM channel selection algorithm ]]\n\n"
        
    # build the graph

    tb = my_top_block(mods[options_tx.modulation],
                      demods[options_rx.modulation],
                      rx_callback,options_tx,
                      options_rx)
    r = gr.enable_realtime_scheduling()
    if r != gr.RT_OK:
        print "Warning: failed to enable realtime scheduling"
    
    tb.start()

    #listening to random frequencies untill a match is found
    running = True

    # Scan all channels first for inital data
    #time.sleep(0.1)

    print "\n[[ Scanning channels for network nodes ]]\n"
    while running:
        ################################################sync mode####################################
        if mode == "sync":
	    if sync_status != True:
                    

                ch,hop_freq = get_freq_rx()
                hop_freq_tx = get_freq_tx()

                tb.txpath.sink.set_freq(hop_freq_tx)
                tb.rxpath.source.set_freq(hop_freq)
                print "RX_FREQ:",hop_freq,"  TX_FREQ:",hop_freq_tx
                ch_energy = tb.rxpath.probe.level() #check if primary user is present
                #print ch_energy,"*"*30
                if int(ch_energy) > threshold: #if primary user is there then dont transmit on this channel
                    continue
                
                nbytes = 5 #int(1e6 * .0003)
                pkt_size = 5
                n = 0
                pktno = 0
                while n < nbytes:
                    if options_tx.from_file is None:
                        data = 's'
                    else:
                        data = source_file.read(pkt_size - 2)
                        if data == '':
                            break;

                    payload = struct.pack('!HsH', pktno & 0xffff,data,ch & 0xffff) #+ data
                            
                    send_pkt(tb,payload)
                    n += len(payload)
                    sys.stderr.write("SEND SYNC PACKET\n")
                    if options_tx.discontinuous and pktno % 5 == 4:
                        time.sleep(1)
                        pktno += 1
                time.sleep(1)
                    
            else:
                print "\n\n[[ Network Node Found: Commencing communications on CHANNEL ", ch, " ]]\n";
                n_attempts_counter = 0
                mode = "traffic"
                data_packet_delivery_count = 0
                sync_status="False"
                start_time = datetime.now() #measuring the time for which the primary user is away
    
        ################################################end of sync mode####################################

        ################################################Communications mode#################################
        if mode == "traffic":
            nbytes = 15
            pkt_size = 15
            data_pktno = 0
            n = 0
            while n < nbytes:
                if options_tx.from_file is None:
                    data = 'dHi how are you' #Sending this message
                else:
                    data = source_file.read(pkt_size - 2)
                    if data == '':
                        break;
    
            
                payload = struct.pack('!15s', data)
                                       
                send_pkt(tb,payload)
                n += len(payload)
                sys.stderr.write("SEND TRAFFIC PACKET\n")
                if options_tx.discontinuous and data_pktno % 5 == 4:
                    time.sleep(1)
                data_pktno += 1
                time.sleep(0.2 + 0.05*int(random.choice([0,1,2,3])))

                if data_packet_delivery_count == data_packet_delivery_count_previous: #checking if the data packet delivery has stagnated
                    n_attempts_counter += 1
                    if n_attempts_counter > n_attempts: #get out of the data channel as it seems that the other node is still trying to rendezvous
                        mode = "sync"
                        continue
		else:
		    data_packet_delivery_count_previous = 0
		    data_packet_delivery_count = 0

		data_packet_delivery_count_previous = data_packet_delivery_count
		ch_energy = tb.rxpath.probe.level() #check if primary user is present
		print "CHANNEL ENERGY:",ch_energy,"\n"
		if ch_energy > threshold: #if primary user is there then dont transmit on this channel
		    stop_time = datetime.now()    
		    _elapsed_time  = stop_time - start_time
		    print "\n[[ Primary User Detected:  Evacuating Current Channel ]]\n"
		    print "\n[[ Scanning channels for network nodes ]]\n"
		    print "\nAbsent time:",_elapsed_time,"\n"
		    mode = "sync"

                

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

