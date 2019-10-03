CCP Algorithm: Constant Rate (or CWND)
======================================

This repository provides a minimal CCP algorithm that sets the cwnd (or rate with a cwnd cap) 
for each new connection to a static value and maintains it for the life of the connection.

It's useful for creating constant bit-rate traffic or as a good starting point example for
writing a new algorithm.

To get started using this algorithm with CCP, please see our
[guide](https://ccp-project.github.io/guide).
