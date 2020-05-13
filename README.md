# testbench-gen
A VHDL test bench generator for combinational and sequential logic, written in Python

# Installation
Once downloaded, the script can simply be executed or invoked with python, e.g. `python tb_gen.py`. No installation is required.

# Usage
Running the script with the `-h` switch will print usage information. Two arguments are required, the first being the name of the testbench JSON file, and the second being the name of the VHDL file to output the generated testbench to. Once generated, this testbench file can be compiled and simulated, for instance with [GHDL](http://ghdl.free.fr/). The script will print out the name of the generated testbench entity, and this can of course also be checked in the output VHDL file.

# Test case file format
Test case files are JSON files. The following properties are read:

* **entity**: the name of the entity to test
* **architecture**: the name of the architecture to use for the given entity
* **library**: the library in which the entity is found
* **clocked**: (bool) whether the entity is clocked
* **clock period**: (integer) clock period in nanoseconds to use if entity is clocked
* **generic_params**: an object where the keys are generic parameter names and the values are the values to use for these parameters
* **input_pins**: an object where the keys are the names of the input pins and the values are the std_logic_vector bus width of these pins (null for single-bit std_logic)
* **clock_pin**: the name of the clock pin (which should not be included with the input pins) if the entity is clocked
* **output pins**: an object of the same format as the input pins
* **test cases**: an array of objects, each object representing a test case. Keys in these test case objects are the names of the input and output pins, and the values are the given (for input pins) or expected (for output pins) values of these pins. Note that the correct quotes will automatically be used to surround these values, and as such the values should not be given their correct VHDL quotes in this file. Another key '\_wait' must also be specified, which controls how long to wait in between setting input pins and checking output pins: 0 means wait for 10 ns, a negative number means wait until that many falling clock edges, and a positive number means wait until that many rising clock edges
