#[macro_use]
extern crate slog;

use slog::Drain;

mod agg_measurement;
mod cc;

fn make_logger() -> slog::Logger {
    let decorator = slog_term::TermDecorator::new().build();
    let drain = slog_term::FullFormat::new(decorator).build().fuse();
    let drain = slog_async::Async::new(drain).build().fuse();
    slog::Logger::root(drain, o!())
}

fn main() {
    let log = make_logger();
    let cfg = cc::NewCCConfig {
        logger: Some(log.clone()),
    };

    info!(log, "Starting Congestion Control");

    portus::start!("netlink", Some(log), cfg).unwrap()
}
