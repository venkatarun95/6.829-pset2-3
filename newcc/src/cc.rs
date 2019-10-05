use fnv::FnvHashMap;
use slog;

use portus::ipc::Ipc;
use portus::lang::Scope;
use portus::{CongAlg, Datapath, DatapathInfo, DatapathTrait, Report};

use crate::agg_measurement::{AggMeasurement, ReportStatus};

pub struct NewCC<T: Ipc> {
    control_channel: Datapath<T>,
    logger: Option<slog::Logger>,
    sc: Scope,
    /// Set this variable to whatever congestion window you want
    cwnd: u32,
    /// Set this variable to whatever rate (packets/second) you want
    rate: u32,
    agg_measurement: AggMeasurement,
    prev_report_time: u64,
}

impl<T: Ipc> NewCC<T> {
    /// Should be called whenever you want self.cwnd or self.rate to be reflected. By default, we
    /// call it for you in `on_report`.
    fn update(&self) {
        self.control_channel
            .update_field(&self.sc, &[("Cwnd", self.cwnd), ("Rate", self.rate)])
            .unwrap()
    }

    fn congestion_control(
        &mut self,
        acked: u32,
        sacked: u32,
        loss: u32,
        inflight: u32,
        rtt: u32,
        min_rtt: u32,
        now: u64,
    ) {
        // Update cwnd (or rate) based on the above signals. Here's what they mean

        // acked - number of packets acked since last call
        // sacked - number of packets that were acked out-of-order since last call
        // loss - number of packets that we think is lost since last call
        // inflight - the latest number of inflight packets (i.e. packets we that have sent but
        //   haven't been acknowledged)
        // rtt - round-trip time of the last acked packet
        // minrtt - minimum rtt among all the packets that were acked since the last call
        // now - ack time (in microseconds) of the last acked packet

        // TODO: Set self.cwnd and self.rate as you wish. Skeletal implementations are given below

        // A default implementation where self.cwnd is a constant
        self.cwnd = 12000;
        // If rate is 0, it will be ignored and only cwnd will be used. If nonzero, units are in
        // ptks/sec
        self.rate = 0;
    }

    fn handle_timeout(&mut self) {
        // A timeout happened. Indicates severe! React accordingly

        self.logger.as_ref().map(|log| {
            warn!(log, "timeout";
                "curr_cwnd (pkts)" => self.cwnd / 1448,
            );
        });
    }
}

#[derive(Clone)]
pub struct NewCCConfig {
    pub logger: Option<slog::Logger>,
}

impl<T: Ipc> CongAlg<T> for NewCCConfig {
    type Flow = NewCC<T>;

    fn name() -> &'static str {
        "newcc"
    }

    fn datapath_programs(&self) -> FnvHashMap<&'static str, String> {
        vec![(
            "newcc",
            "(def
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
                (report)
            )
            (when (|| Flow.was_timeout (> Report.loss 0))
                (:= Micros 0)
                (report)
            )
            (when (> Micros (/ basertt 2))
                (:= Micros 0)
                (report)
            )"
            .to_string(),
        )]
        .into_iter()
        .collect()
    }

    fn new_flow(&self, control: Datapath<T>, info: DatapathInfo) -> Self::Flow {
        let mut s = NewCC {
            control_channel: control,
            logger: self.logger.clone(),
            cwnd: 15000,
            rate: 0,
            sc: Default::default(),
            // TODO: 0.5 says that it will report a measurement once every half RTT. You may
            // increase this. If you want to recrease it, change the 4rth last line in the program
            // in `datapath_programs`
            agg_measurement: AggMeasurement::new(0.5),
            prev_report_time: 0,
        };

        self.logger.as_ref().map(|log| {
            info!(log, "starting new flow"; "sock_id" => info.sock_id);
        });

        s.sc = s.control_channel.set_program("newcc", None).unwrap();
        s.update();
        s
    }
}

impl<T: Ipc> portus::Flow for NewCC<T> {
    fn on_report(&mut self, _sock_id: u32, m: Report) {
        let (report_status, was_timeout, acked, sacked, loss, inflight, rtt, min_rtt, now) =
            self.agg_measurement.report(m, &self.sc);
        println!(
            "Report {:?}",
            (
                &report_status,
                was_timeout,
                acked,
                sacked,
                loss,
                inflight,
                rtt,
                min_rtt,
                now
            )
        );
        if report_status == ReportStatus::UrgentReport {
            if was_timeout {
                self.handle_timeout();
            }
        } else if report_status == ReportStatus::NoReport || acked + loss + sacked == 0 {
            self.congestion_control(acked, sacked, loss, inflight, rtt, min_rtt, now);
        } else {
        }

        // Send decisions to CCP
        self.update();

        self.logger.as_ref().map(|log| {
            debug!(log, "got ack";
                   "acked(pkts)" => acked / 1448u32,
                   "curr_cwnd (pkts)" => self.cwnd / 1460,
                   "loss" => loss,
                   "sacked" => sacked,
                   "rtt" => rtt,
                   "report_interval" => now - self.prev_report_time,
            );
        });
        self.prev_report_time = now;
    }
}
