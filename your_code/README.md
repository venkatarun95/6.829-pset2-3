CCP, the tool you will be using to write your congestion control algorithms, is structured as a kernel module that connects to userspace programs. Our initialization scripts will load the kernel module, making `ccp` available as a congestion control algorithm. To write your own congestion control algorithm, you will write a user-space program which connects to the kernel module to instruct it on what to do. To enable your algorithm, simply run your userspace program before starting the experiments.

We have provided skeleton code for this user-space program in Python and Rust. We strongly recommend using Rust, and we will support only Rust, but you are free to use either.

CCP works by running a datapath program that your program supplies on every ack. The values this program accumulates are reported to userspace when `(userpsace)` is called. See the CCP documentation for details.

Rust
----

We have placed a skeleton program (called 'crate') in the `newcc` directory. You can implement many congestion control algorithms by modifying the `NewCC::congestio_control` in `src/lib.rs`. The comments should help you in doing this. To build, use `cargo build` somewhere in the `newcc` directory. Then run the `newcc/target/debug/newcc` binary that is produced as root. Feel free to modify the entire crate as you see fit, including the datapath programs.

Python
------

Here, again, you can implement many congestion control programs by simply modifying the `on_report` function. Run it using `python3 newcc.py` and run your programs
