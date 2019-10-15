import sys
import portus

class NewCCFlow():

  def __init__(self, datapath, datapath_info):
    sys.stdout.write("new flow\n")
    self.datapath = datapath
    self.datapath_info = datapath_info
    self.cwnd = 1200
    self.rate = 0

    l = [("Cwnd", int(self.cwnd)), ("Rate", int(self.rate))]
    self.datapath.set_program("default", l)

  def on_report(self, r):
    sys.stdout.write(
        "[report] cwnd={:02d}p rtt={:03d}ms acked={:03d}p loss={:02d}p\n".
        format(int(self.cwnd / self.datapath_info.mss), int(r.rtt / 1000.0),
               int(r.acked / self.datapath_info.mss), r.loss))

    # TODO: Implement your congestion control algorithm here. As an example, we
    # have implemented AIMD
    if r.loss > 0:
      self.cwnd /= 2
    else:
      self.cwnd += 1448 * r.acked / self.cwnd
    self.cwnd = max(self.cwnd, 3000)

    self.datapath.update_field("Cwnd", int(self.cwnd))


class NewCC(portus.AlgBase):

  def datapath_programs(self):
    # This 'datapath program' instructs CCP on what variables to return to the
    # userspace program, and at what intervals. See CCP documentation for
    # details.
    return {
        "default":
        """\
            (def
                (Report
                    (volatile acked 0)
                    (volatile sacked 0)
                    (volatile loss 0)
                    (volatile inflight 0)
                    (volatile timeout 0)
                    (volatile rtt 0)
                    (volatile minrtt +infinity)
                    (volatile numpkts 0)
                    (volatile now 0)
               )
                (basertt +infinity)
            )
            (when true
                (:= Report.acked (+ Report.acked Ack.bytes_acked))
                (:= Report.inflight Flow.packets_in_flight)
                (:= Report.rtt Flow.rtt_sample_us)
                (:= Report.minrtt (min Report.minrtt Flow.rtt_sample_us))
                (:= basertt (min basertt Flow.rtt_sample_us))
                (:= Report.sacked (+ Report.sacked Ack.packets_misordered))
                (:= Report.loss Ack.lost_pkts_sample)
                (:= Report.timeout Flow.was_timeout)
                (:= Report.now Ack.now)
                (fallthrough)
            )
            (when (|| Flow.was_timeout (> Report.loss 0))
                (:= Micros 0)
                (report)
            )
            (when (> Micros (/ basertt 2))
                (:= Micros 0)
                (report)
            )
            """
    }

  def new_flow(self, datapath, datapath_info):
    return NewCCFlow(datapath, datapath_info)


def main():
  alg = NewCC()
  portus.start("netlink", alg, debug=True)


if __name__ == '__main__':
  main()
