import sys
import portus
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--cwnd', type=int, required=True)
args = parser.parse_args()


class ConstFlow():

  def __init__(self, datapath, datapath_info):
    sys.stdout.write("new flow\n")
    self.datapath = datapath
    self.datapath_info = datapath_info
    self.cwnd = args.cwnd
    self.datapath.set_program("default", [("Cwnd", int(self.cwnd))])

  def on_report(self, r):
    sys.stdout.write(
        "[report] cwnd={:02d}p rtt={:03d}ms acked={:03d}p loss={:02d}p\n".
        format(int(self.cwnd / self.datapath_info.mss), int(r.rtt / 1000.0),
               int(r.acked / self.datapath_info.mss), r.loss))
    self.datapath.update_field("Cwnd", int(self.cwnd))


class Const(portus.AlgBase):

  def datapath_programs(self):
    return {
        "default":
        """\
                (def (Report
                    (volatile acked 0)
                    (volatile loss 0)
                    (volatile rtt 0)
                ))
                (when true
                    (:= Report.rtt Flow.rtt_sample_us)
                    (:= Report.acked (+ Report.acked Ack.bytes_acked))
                    (:= Report.loss Ack.lost_pkts_sample)
                    (fallthrough)
                )
                (when (> Micros 500000)
                    (report)
                    (:= Micros 0)
                )
            """
    }

  def new_flow(self, datapath, datapath_info):
    return ConstFlow(datapath, datapath_info)


def main():
  alg = Const()
  portus.start("netlink", alg, debug=True)


if __name__ == '__main__':
  main()
